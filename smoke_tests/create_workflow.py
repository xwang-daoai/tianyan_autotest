"""
Create a workflow via the API so it can be used by the smoke test.
Hardcoded values to avoid prompting for parameters.
"""

import json
from pathlib import Path

import requests

BASE_URL = "http://ipc1.daoai.ca:38080"
AUTH_TOKEN = None  # fill in a token if required
AUTH_HEADER = "Authorization"
WORKFLOW_NAME = "Smoke Test Workflow"
VERIFY_TLS = True  # set to False for self-signed HTTPS endpoints
# Where to read the workflow definition.
WORKFLOW_DEFINITION_FILE = Path(__file__).with_name("workflow_definition.json")
# Where to store the created workflow id so later steps can reuse it.
WORKFLOW_CREATED_ID_FILE = Path(__file__).with_name("workflow_created_id.txt")
DEFAULT_DEFINITION = {
    "version": "1.0",
    "inputs": [
        {
            "type": "WorkflowImage",
            "name": "image",
        }
    ],
    "steps": [],
    "outputs": [],
}


def load_definition() -> dict:
    if WORKFLOW_DEFINITION_FILE.exists():
        text = WORKFLOW_DEFINITION_FILE.read_text(encoding="utf-8").strip()
        if text:
            try:
                return json.loads(text)
            except json.JSONDecodeError as exc:
                raise AssertionError(f"{WORKFLOW_DEFINITION_FILE.name} is not valid JSON: {exc}") from exc
    return DEFAULT_DEFINITION


def create_workflow() -> dict:
    session = requests.Session()
    session.verify = VERIFY_TLS
    session.headers.update({"Content-Type": "application/json"})
    if AUTH_TOKEN:
        session.headers[AUTH_HEADER] = f"Bearer {AUTH_TOKEN}"

    definition = load_definition()
    payload = {"name": WORKFLOW_NAME, "definition": definition}

    resp = session.post(f"{BASE_URL.rstrip('/')}/workflows", json=payload)
    if resp.status_code not in (200, 201, 202):
        raise AssertionError(
            f"Failed to create workflow: status={resp.status_code}, body={resp.text[:500]}"
        )
    return resp.json()


if __name__ == "__main__":
    result = create_workflow()
    workflow_id = None
    if isinstance(result, dict):
        workflow_id = result.get("workflow_id") or result.get("id")
    if workflow_id:
        WORKFLOW_CREATED_ID_FILE.write_text(str(workflow_id), encoding="utf-8")
    print(f"Created workflow: id={workflow_id} body={result}")