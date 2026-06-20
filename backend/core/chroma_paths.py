"""Shared ChromaDB persist directory resolution."""

from __future__ import annotations

import os
from pathlib import Path

_ROOT = Path(__file__).parent.parent.parent

# Optional Railway persistent volume — only use when explicitly configured.
_RAILWAY_VOLUME_DIR = Path("/app/chroma_db")


def chroma_persist_dir() -> Path:
    """
    Return Chroma persist path.

    On Railway the default is /tmp/chroma_db (container-local, writable SQLite).
    Set CHROMA_PERSIST_DIR=/app/chroma_db only after a volume is attached and a
    successful restore has been verified on that mount.
    """
    override = os.getenv("CHROMA_PERSIST_DIR", "").strip()
    if override:
        return Path(override)
    if os.getenv("RAILWAY_ENVIRONMENT"):
        return Path("/tmp/chroma_db")
    return _ROOT / "chroma_db"
