"""
Knowledge bank maintenance status — shown during Chroma restore / redeploy.

Set KNOWLEDGE_BANK_UPDATING=true on Railway before a FORCE redeploy so users
see a friendly message instead of empty answers. Optional
KNOWLEDGE_BANK_UPDATE_STARTED_AT (ISO-8601) anchors the ETA; otherwise the
server uses the time maintenance was first detected.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from config.settings import get_settings

_DETAIL = "KNOWLEDGE_BANK_UPDATING"


def _env_truthy(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes")


def _parse_started_at(raw: str) -> Optional[datetime]:
    if not raw.strip():
        return None
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def maintenance_flag_enabled() -> bool:
    return _env_truthy("KNOWLEDGE_BANK_UPDATING")


def get_eta_minutes() -> int:
    return max(1, get_settings().chroma_restore_eta_minutes)


def resolve_started_at(app: Any) -> datetime:
    """Return UTC time maintenance began (env, app state, or now)."""
    env_raw = os.getenv("KNOWLEDGE_BANK_UPDATE_STARTED_AT", "").strip()
    parsed = _parse_started_at(env_raw)
    if parsed:
        return parsed

    state_started = getattr(app.state, "maintenance_started_at", None)
    if isinstance(state_started, datetime):
        if state_started.tzinfo is None:
            return state_started.replace(tzinfo=timezone.utc)
        return state_started.astimezone(timezone.utc)

    return datetime.now(timezone.utc)


def is_knowledge_bank_updating(app: Any) -> bool:
    """True when chat retrieval should be blocked with a maintenance message."""
    if maintenance_flag_enabled():
        return True

    retriever = getattr(app.state, "retriever", None)
    if retriever is None:
        return True

    try:
        return retriever.document_count() == 0
    except Exception:
        return True


def format_check_back_at(dt: datetime) -> str:
    """Human-readable local time hint (UTC stored, formatted for display)."""
    return dt.astimezone(timezone.utc).strftime("%H:%M UTC on %d %b %Y")


def build_maintenance_payload(app: Any) -> dict[str, Any]:
    started = resolve_started_at(app)
    eta = get_eta_minutes()
    check_back = started + timedelta(minutes=eta)
    message = (
        "The application knowledge bank is being updated. "
        f"Please check back at {format_check_back_at(check_back)}."
    )
    return {
        "detail": _DETAIL,
        "maintenance": {
            "active": True,
            "message": message,
            "check_back_at": check_back.isoformat(),
            "started_at": started.isoformat(),
            "eta_minutes": eta,
        },
    }


def build_health_payload(app: Any) -> dict[str, Any]:
    retriever = getattr(app.state, "retriever", None)
    count = retriever.document_count() if retriever else 0
    updating = is_knowledge_bank_updating(app)

    payload: dict[str, Any] = {
        "status": "updating" if updating else "ok",
        "chromadb": {"document_count": count},
    }
    if updating:
        payload["maintenance"] = build_maintenance_payload(app)["maintenance"]
    return payload
