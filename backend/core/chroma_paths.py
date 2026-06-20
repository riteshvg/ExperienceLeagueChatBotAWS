"""Shared ChromaDB persist directory resolution."""

from __future__ import annotations

import os
from pathlib import Path

_ROOT = Path(__file__).parent.parent.parent

# Railway persistent volume (attach in Railway dashboard → Volumes → mount path).
_RAILWAY_VOLUME_DIR = Path("/app/chroma_db")


def chroma_persist_dir() -> Path:
    """
    Return Chroma persist path.

    On Railway, prefer the persistent volume so code redeploys do not wipe the
    index and re-download S3. Ephemeral /tmp is only used when the volume path
    is unavailable (local Railway emulator, misconfigured deploy).
    """
    override = os.getenv("CHROMA_PERSIST_DIR", "").strip()
    if override:
        return Path(override)
    if os.getenv("RAILWAY_ENVIRONMENT"):
        if _RAILWAY_VOLUME_DIR.parent.is_dir():
            return _RAILWAY_VOLUME_DIR
        return Path("/tmp/chroma_db")
    return _ROOT / "chroma_db"
