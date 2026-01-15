from typing import Any, Dict, Optional

from .api_client import ApiClient
from .utils import truncate


def create_camera(api: ApiClient, name: str, stream_url: str, workflow_id: int) -> int:
    payload = {
        "name": name,
        "stream_url": stream_url,
        "workflow_id": workflow_id,
    }
    resp = api.request_json("POST", "/cameras", json=payload)
    if not isinstance(resp, dict):
        raise AssertionError(f"Unexpected camera response: {resp}")
    camera_id = resp.get("id") or resp.get("camera_id") or resp.get("cameraId")
    if camera_id is None:
        raise AssertionError(f"Camera id missing in response: {resp}")
    return camera_id


def assign_workflow(api: ApiClient, camera_id: int, workflow_id: int) -> Optional[str]:
    payload = {"camera_ids": [camera_id], "workflow_id": workflow_id}
    resp = api.request("POST", "/cameras/assign-workflow", json=payload)
    if resp.status_code not in (200, 201, 202, 204):
        return f"{resp.status_code} {truncate(resp.text,300)}"
    return None


def start_camera(api: ApiClient, camera_id: int) -> None:
    api.request_json("POST", f"/cameras/{camera_id}/start")


def stop_camera(api: ApiClient, camera_id: int, stop_monitoring: bool = False) -> None:
    payload = {"stop_monitoring": stop_monitoring}
    api.request_json("POST", f"/cameras/{camera_id}/stop", json=payload, expected_status=(200, 202, 204))


def start_monitoring(api: ApiClient, camera_id: int) -> None:
    api.request_json("POST", f"/cameras/{camera_id}/start-monitoring")


def stop_monitoring(api: ApiClient, camera_id: int) -> None:
    api.request_json("POST", f"/cameras/{camera_id}/stop-monitoring", expected_status=(200, 202, 204))


def capture(api: ApiClient, camera_id: int):
    return api.request("GET", f"/cameras/{camera_id}/capture")


def get_token(api: ApiClient, camera_id: int, viewer_identity: str = "smoke-test") -> Any:
    payload = {"viewer_identity": viewer_identity}
    return api.request_json("POST", f"/cameras/{camera_id}/token", json=payload)


def delete_camera(api: ApiClient, camera_id: int) -> None:
    api.request_json("DELETE", f"/cameras/{camera_id}", expected_status=(200, 202, 204))