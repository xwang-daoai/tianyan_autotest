import os
from typing import Any, Dict, Optional

import requests

from .utils import truncate


class ApiClient:
    def __init__(
        self,
        base_url: str,
        auth_token: Optional[str],
        auth_header: str,
        auth_prefix: str,
        verify_tls: bool,
        request_timeout: float,
    ):
        self.base_url = base_url.rstrip("/")
        self.request_timeout = request_timeout
        self.session = requests.Session()
        self.session.verify = verify_tls
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if auth_token:
            token_value = f"{auth_prefix} {auth_token}".strip() if auth_prefix else auth_token
            headers[auth_header] = token_value
        self.session.headers.update(headers)

    def _full_url(self, path: str) -> str:
        if path.startswith("http"):
            return path
        return f"{self.base_url}/{path.lstrip('/')}"

    def request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = self._full_url(path)
        resp = self.session.request(method, url, timeout=self.request_timeout, **kwargs)
        return resp

    def request_json(
        self,
        method: str,
        path: str,
        expected_status=(200, 201, 202, 204),
        **kwargs,
    ) -> Any:
        resp = self.request(method, path, **kwargs)
        if resp.status_code not in expected_status:
            body = truncate(resp.text, 500)
            raise AssertionError(f"{method} {path} failed: {resp.status_code} {body}")
        if resp.status_code == 204:
            return None
        try:
            return resp.json()
        except ValueError:
            return resp.text