# Smoke Test & Performance Probe

## Requirements
- Python 3.10+
- Install deps: `pip install -r requirements.txt`

## Env vars (override defaults)
- `BASE_URL` (default `http://ipc1.daoai.ca:38080`)
- `AUTH_TOKEN` (optional)
- `AUTH_HEADER` (default `Authorization`)
- `AUTH_PREFIX` (default `Bearer`; set empty to skip prefix)
- `VERIFY_TLS` (default `true`; set `false` to disable verification)
- `RTSP_URL` (**required**)
- `WORKFLOW_NAME` (default `Smoke Test Workflow`)
- `CAMERA_NAME` (default `Smoke Test Camera`)
- `THRESHOLD_SECONDS` (default `120`)
- `CYCLES` (default `2`)
- `POLL_INTERVAL_SECONDS` (default `1`)
- `REQUEST_TIMEOUT_SECONDS` (default `10`)

## Run
cd smoke_tests
python smoke_test.py
