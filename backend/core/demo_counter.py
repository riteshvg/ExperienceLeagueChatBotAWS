"""
Demo usage counter — persists to data/demo_usage.json.
Thread-safe for concurrent FastAPI requests.
"""

import json
from pathlib import Path
from threading import Lock

_ROOT = Path(__file__).parent.parent.parent
_FILE = _ROOT / "data" / "demo_usage.json"
_LIMIT = 5
_lock = Lock()


def _read() -> int:
    try:
        return json.loads(_FILE.read_text()).get("count", 0)
    except Exception:
        return 0


def _write(count: int) -> None:
    _FILE.parent.mkdir(parents=True, exist_ok=True)
    _FILE.write_text(json.dumps({"count": count}))


def get_status() -> dict:
    count = _read()
    return {
        "questions_used": count,
        "questions_limit": _LIMIT,
        "questions_remaining": max(0, _LIMIT - count),
        "exhausted": count >= _LIMIT,
    }


def increment() -> dict:
    """Increment counter and return updated status. Raises ValueError if exhausted."""
    with _lock:
        count = _read()
        if count >= _LIMIT:
            raise ValueError("Demo limit reached")
        _write(count + 1)
        return get_status()


def reset() -> dict:
    with _lock:
        _write(0)
        return get_status()
