import json
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List


def aggregate(values: List[float]) -> Dict[str, Any]:
    if not values:
        return {"avg": None, "max": None}
    return {"avg": mean(values), "max": max(values)}


def write_report_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def write_report_md(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    lines.append(f"# Smoke Test Report\n")
    lines.append(f"- run_id: {data.get('run_id')}")
    lines.append(f"- base_url: {data.get('base_url')}")
    lines.append(f"- rtsp_url: {data.get('rtsp_url')}")
    lines.append(f"- threshold_seconds: {data.get('threshold_seconds')}")
    lines.append(f"- cycles: {data.get('cycles')}")
    lines.append("")

    lines.append("## Steps")
    for step in data.get("steps", []):
        status = step.get("status")
        dur = step.get("duration_seconds")
        lines.append(f"- {step.get('name')}: {status}, {dur:.3f}s" if dur is not None else f"- {step.get('name')}: {status}")
    lines.append("")

    cycles = data.get("cycles_detail", [])
    if cycles:
        lines.append("## Cycles")
        lines.append("| cycle | start_camera | start_monitoring | first_frame | get_token | stop_monitoring | stop_camera |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- |")
        for c in cycles:
            def fmt(v): return f"{v:.3f}s" if isinstance(v, (int, float)) else "-"
            lines.append(
                f"| {c.get('cycle')} | {fmt(c.get('t_start_camera_api'))} | {fmt(c.get('t_start_monitoring_api'))} | "
                f"{fmt(c.get('t_first_frame'))} | {fmt(c.get('t_get_token'))} | "
                f"{fmt(c.get('t_stop_monitoring_api'))} | {fmt(c.get('t_stop_camera_api'))} |"
            )
        lines.append("")

    summary = data.get("summary", {})
    lines.append("## Summary")
    for k, v in summary.items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")