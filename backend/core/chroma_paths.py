"""Shared ChromaDB persist directory resolution."""

from __future__ import annotations

import os
from pathlib import Path

_ROOT = Path(__file__).parent.parent.parent

# Railway persistent volume — Chroma SQLite is unreliable here unless verified.
_RAILWAY_VOLUME_DIR = Path("/app/chroma_db")
_RAILWAY_TMP_DIR = Path("/tmp/chroma_db")


def _env_truthy(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes")


def chroma_persist_dir() -> Path:
    """
    Return Chroma persist path.

    On Railway the default is /tmp/chroma_db. CHROMA_PERSIST_DIR=/app/chroma_db is
    ignored unless CHROMA_USE_VOLUME=true (volume + SQLite must be verified first).
    """
    override = os.getenv("CHROMA_PERSIST_DIR", "").strip()
    if os.getenv("RAILWAY_ENVIRONMENT"):
        if _env_truthy("CHROMA_USE_VOLUME") and override:
            return Path(override)
        if override and Path(override) not in (_RAILWAY_VOLUME_DIR, _RAILWAY_TMP_DIR):
            return Path(override)
        return _RAILWAY_TMP_DIR
    if override:
        return Path(override)
    return _ROOT / "chroma_db"
