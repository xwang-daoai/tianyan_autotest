import json
from pathlib import Path
from typing import Any, Dict, Optional

from .utils import truncate
from .api_client import ApiClient

DEFAULT_DEFINITION: Dict[str, Any] = {
    "version": "1.0",
    "inputs": [{"type": "WorkflowImage", "name": "image"}],
    "steps": [],
    "outputs": [],
}


def load_definition(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return DEFAULT_DEFINITION
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return DEFAULT_DEFINITION
    try:
        data = json.loads(text)
        return data if data else DEFAULT_DEFINITION
    except json.JSONDecodeError as exc:
        raise AssertionError(f"{path.name} invalid JSON: {truncate(str(exc), 200)}") from exc


def create_workflow(api: ApiClient, name: str, definition: Dict[str, Any]) -> int:
    payload = {"name": name, "definition": definition}
    resp = api.request_json("POST", "/workflows", json=payload)
    if not isinstance(resp, dict):
        raise AssertionError(f"Unexpected workflow response: {resp}")
    workflow_id = resp.get("workflow_id") or resp.get("id")
    if workflow_id is None:
        raise AssertionError(f"Workflow id missing in response: {resp}")
    return workflow_id


def delete_workflow(api: ApiClient, workflow_id: int) -> None:
    api.request_json("DELETE", f"/workflows/{workflow_id}", expected_status=(200, 202, 204))