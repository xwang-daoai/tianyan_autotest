import os
import time
from typing import Any, Callable, Optional


def env_bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.lower() in {"1", "true", "yes", "y", "on"}


def env_int(name: str, default: int) -> int:
    val = os.getenv(name)
    if val is None:
        return default
    try:
        return int(val)
    except ValueError:
        return default


def env_float(name: str, default: float) -> float:
    val = os.getenv(name)
    if val is None:
        return default
    try:
        return float(val)
    except ValueError:
        return default


def poll_until(
    func: Callable[[], Any],
    condition: Callable[[Any], bool],
    timeout: float,
    interval: float,
) -> Any:
    """Poll func until condition(result) or timeout."""
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        last = func()
        if condition(last):
            return last
        time.sleep(interval)
    return last


def now_ms() -> int:
    return int(time.time() * 1000)


def duration_seconds(start_ms: int, end_ms: int) -> float:
    return (end_ms - start_ms) / 1000.0


def truncate(text: str, limit: int = 500) -> str:
    if text is None:
        return ""
    if len(text) <= limit:
        return text
    return text[:limit] + "...(truncated)"