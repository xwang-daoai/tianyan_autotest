import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from lib.api_client import ApiClient
from lib.workflow import load_definition, create_workflow, delete_workflow
from lib.camera import (
    assign_workflow,
    capture,
    create_camera,
    delete_camera,
    get_token,
    start_camera,
    start_monitoring,
    stop_camera,
    stop_monitoring,
)
from lib.metrics import aggregate, write_report_json, write_report_md
from lib.utils import (
    env_bool,
    env_float,
    env_int,
    now_ms,
    duration_seconds,
    poll_until,
    truncate,
)

BASE_DIR = Path(__file__).parent
REPORTS_DIR = BASE_DIR / "reports"

# Config
BASE_URL = os.getenv("BASE_URL", "http://ipc1.daoai.ca:38080")
AUTH_TOKEN = os.getenv("AUTH_TOKEN")
AUTH_HEADER = os.getenv("AUTH_HEADER", "Authorization")
AUTH_PREFIX = os.getenv("AUTH_PREFIX", "Bearer")
VERIFY_TLS = env_bool("VERIFY_TLS", True)
RTSP_URL = os.getenv("RTSP_URL")
WORKFLOW_NAME = os.getenv("WORKFLOW_NAME", "Smoke Test Workflow")
CAMERA_NAME = os.getenv("CAMERA_NAME", "Smoke Test Camera")
THRESHOLD_SECONDS = env_float("THRESHOLD_SECONDS", 120.0)
CYCLES = env_int("CYCLES", 2)
POLL_INTERVAL_SECONDS = env_float("POLL_INTERVAL_SECONDS", 1.0)
REQUEST_TIMEOUT_SECONDS = env_float("REQUEST_TIMEOUT_SECONDS", 10.0)
DEFINITION_PATH = BASE_DIR / "workflow_definition.json"


def fail(msg: str):
    print(f"[FAIL] {msg}")
    sys.exit(1)


def main():
    if not RTSP_URL:
        fail("RTSP_URL is required (env)")

    run_id = f"smoke-{uuid.uuid4().hex[:8]}"
    print(f"Run id: {run_id}")

    api = ApiClient(
        base_url=BASE_URL,
        auth_token=AUTH_TOKEN,
        auth_header=AUTH_HEADER,
        auth_prefix=AUTH_PREFIX,
        verify_tls=VERIFY_TLS,
        request_timeout=REQUEST_TIMEOUT_SECONDS,
    )

    steps: List[Dict[str, Any]] = []
    cycles_detail: List[Dict[str, Any]] = []

    workflow_id: Optional[int] = None
    camera_id: Optional[int] = None

    def record_step(name: str, status: str, duration: Optional[float], error: Optional[str] = None):
        steps.append({"name": name, "status": status, "duration_seconds": duration, "error": error})

    try:
        # Create workflow
        t0 = now_ms()
        definition = load_definition(DEFINITION_PATH)
        try:
            workflow_id = create_workflow(api, WORKFLOW_NAME, definition)
            record_step("create_workflow", "ok", duration_seconds(t0, now_ms()))
            print(f"[OK] workflow created id={workflow_id}")
        except Exception as exc:  # noqa: BLE001
            record_step("create_workflow", "fail", duration_seconds(t0, now_ms()), str(exc))
            raise

        # Create camera
        t0 = now_ms()
        try:
            camera_id = create_camera(api, CAMERA_NAME, RTSP_URL, workflow_id)
            record_step("create_camera", "ok", duration_seconds(t0, now_ms()))
            print(f"[OK] camera created id={camera_id}")
        except Exception as exc:  # noqa: BLE001
            record_step("create_camera", "fail", duration_seconds(t0, now_ms()), str(exc))
            raise

        # Optional assign workflow
        t0 = now_ms()
        assign_err = assign_workflow(api, camera_id, workflow_id)
        record_step(
            "assign_workflow",
            "warning" if assign_err else "ok",
            duration_seconds(t0, now_ms()),
            assign_err,
        )
        if assign_err:
            print(f"[WARN] assign_workflow failed: {assign_err}")

        # Cycles
        first_frame_times: List[float] = []
        stop_camera_times: List[float] = []
        for i in range(1, CYCLES + 1):
            cycle_data: Dict[str, Any] = {"cycle": i}
            print(f"[CYCLE {i}] start")

            # start camera
            t0 = now_ms()
            start_camera(api, camera_id)
            cycle_data["t_start_camera_api"] = duration_seconds(t0, now_ms())

            # start monitoring
            t0 = now_ms()
            start_monitoring(api, camera_id)
            cycle_data["t_start_monitoring_api"] = duration_seconds(t0, now_ms())

            # first frame
            cap_start = now_ms()
            last_resp = None

            def try_capture():
                nonlocal last_resp
                last_resp = capture(api, camera_id)
                return last_resp

            resp = poll_until(
                try_capture,
                lambda r: r is not None and r.status_code == 200 and r.content,
                timeout=THRESHOLD_SECONDS,
                interval=POLL_INTERVAL_SECONDS,
            )
            cap_end = now_ms()
            t_first_frame = duration_seconds(cap_start, cap_end)
            cycle_data["t_first_frame"] = t_first_frame
            if resp is None or resp.status_code != 200 or not resp.content:
                body = truncate(last_resp.text if last_resp else "", 300)
                record_step(
                    f"cycle_{i}_first_frame",
                    "fail",
                    t_first_frame,
                    f"timeout or bad response: {body}",
                )
                raise AssertionError(f"First frame failed in cycle {i}: {body}")
            if t_first_frame > THRESHOLD_SECONDS:
                record_step(
                    f"cycle_{i}_first_frame",
                    "fail",
                    t_first_frame,
                    f"exceeded threshold {THRESHOLD_SECONDS}s",
                )
                raise AssertionError(f"First frame exceeded threshold {THRESHOLD_SECONDS}s")
            record_step(f"cycle_{i}_first_frame", "ok", t_first_frame)
            first_frame_times.append(t_first_frame)

            # token (with retry)
            tok_start = now_ms()
            token_err = None
            token_resp = None
            for attempt in range(3):
                try:
                    token_resp = get_token(api, camera_id)
                    token_err = None
                    break
                except Exception as exc:  # noqa: BLE001
                    token_err = str(exc)
                    time.sleep(1)
            cycle_data["t_get_token"] = duration_seconds(tok_start, now_ms())
            if token_err:
                record_step(f"cycle_{i}_get_token", "warning", cycle_data["t_get_token"], token_err)
                print(f"[WARN] token failed in cycle {i}: {token_err}")
            else:
                record_step(f"cycle_{i}_get_token", "ok", cycle_data["t_get_token"])

            # stop monitoring
            t0 = now_ms()
            stop_monitoring(api, camera_id)
            cycle_data["t_stop_monitoring_api"] = duration_seconds(t0, now_ms())

            # stop camera
            t0 = now_ms()
            stop_camera(api, camera_id, stop_monitoring=False)
            cycle_data["t_stop_camera_api"] = duration_seconds(t0, now_ms())
            stop_camera_times.append(cycle_data["t_stop_camera_api"])

            cycles_detail.append(cycle_data)
            print(f"[CYCLE {i}] done")

        # Summary
        summary = {
            "first_frame": aggregate(first_frame_times),
            "stop_camera": aggregate(stop_camera_times),
            "threshold_seconds": THRESHOLD_SECONDS,
            "pass": all(t <= THRESHOLD_SECONDS for t in first_frame_times),
        }

        report = {
            "run_id": run_id,
            "timestamp": time.time(),
            "base_url": BASE_URL,
            "rtsp_url": RTSP_URL,
            "steps": steps,
            "cycles": CYCLES,
            "cycles_detail": cycles_detail,
            "threshold_seconds": THRESHOLD_SECONDS,
            "summary": summary,
        }
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        write_report_json(REPORTS_DIR / "report.json", report)
        write_report_md(REPORTS_DIR / "report.md", report)
        print(f"[DONE] report written to {REPORTS_DIR}")
    finally:
        # Cleanup
        if camera_id is not None:
            try:
                stop_monitoring(api, camera_id)
            except Exception:
                pass
            try:
                stop_camera(api, camera_id, stop_monitoring=True)
            except Exception:
                pass
            try:
                delete_camera(api, camera_id)
            except Exception:
                pass
        if workflow_id is not None:
            try:
                delete_workflow(api, workflow_id)
            except Exception:
                pass


if __name__ == "__main__":
    main()