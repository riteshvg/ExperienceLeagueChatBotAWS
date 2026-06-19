"""Shared ChromaDB persist directory resolution."""

from __future__ import annotations

import os
from pathlib import Path

_ROOT = Path(__file__).parent.parent.parent


def chroma_persist_dir() -> Path:
    """Return writable Chroma path. Railway uses /tmp (ephemeral) after S3 restore."""
    override = os.getenv("CHROMA_PERSIST_DIR", "").strip()
    if override:
        return Path(override)
    if os.getenv("RAILWAY_ENVIRONMENT"):
        return Path("/tmp/chroma_db")
    return _ROOT / "chroma_db"
