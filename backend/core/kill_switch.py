"""
Kill switch — in-memory cache with 30s TTL backed by system_config PostgreSQL table.

Usage:
  is_api_enabled()  → bool (cached, 30s TTL)
  set_enabled(bool) → writes to DB and invalidates cache
"""

import time

_CACHE_TTL = 30.0
_KEY = "api_enabled"

_cache: dict = {"enabled": True, "expires_at": 0.0}


def is_api_enabled() -> bool:
    now = time.monotonic()
    if now < _cache["expires_at"]:
        return _cache["enabled"]

    try:
        from backend.core import google_db
        raw = google_db.get_system_config(_KEY)
        enabled = (raw or "true").lower() not in ("false", "0", "off")
    except Exception:
        enabled = True  # fail open

    _cache["enabled"] = enabled
    _cache["expires_at"] = now + _CACHE_TTL
    return enabled


def set_enabled(enabled: bool) -> None:
    from backend.core import google_db
    google_db.set_system_config(_KEY, "true" if enabled else "false")
    _cache["expires_at"] = 0.0  # invalidate immediately
