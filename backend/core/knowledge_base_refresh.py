"""
Knowledge base last-refreshed timestamp for the admin dashboard.

Production refreshes via GHA → S3 (not the local admin refresh pipeline), so we
resolve the timestamp from S3 object metadata with local fallbacks.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).parent.parent.parent
_CHROMA_S3_KEY = os.getenv("CHROMA_S3_KEY", "chroma_db/chroma_db.tar.gz")
_CHROMA_META_KEY = "state/chroma_last_refreshed.json"
_MANIFEST_KEY = "state/sync_manifest.json"
_S3_BUCKET = os.getenv("AWS_S3_BUCKET", "experienceleaguechatbot")


def _parse_iso(value: str | None) -> str | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except ValueError:
        return None


def _s3_client():
    import boto3
    return boto3.client(
        "s3",
        region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
    )


def _s3_head_last_modified(key: str) -> tuple[str | None, str]:
    bucket = os.getenv("AWS_S3_BUCKET", _S3_BUCKET)
    if not bucket:
        return None, ""
    try:
        resp = _s3_client().head_object(Bucket=bucket, Key=key)
        modified = resp.get("LastModified")
        if modified:
            return modified.astimezone(timezone.utc).isoformat(), f"s3:{key}"
    except Exception as exc:
        logger.debug("S3 head_object failed for %s: %s", key, exc)
    return None, ""


def _s3_chroma_metadata() -> tuple[str | None, str]:
    bucket = os.getenv("AWS_S3_BUCKET", _S3_BUCKET)
    if not bucket:
        return None, ""
    try:
        obj = _s3_client().get_object(Bucket=bucket, Key=_CHROMA_META_KEY)
        data = json.loads(obj["Body"].read().decode("utf-8"))
        ts = _parse_iso(data.get("uploaded_at"))
        if ts:
            return ts, "s3:chroma_last_refreshed.json"
    except Exception as exc:
        logger.debug("Chroma metadata JSON unavailable: %s", exc)
    return None, ""


def _s3_chroma_metadata_record() -> dict[str, Any]:
    bucket = os.getenv("AWS_S3_BUCKET", _S3_BUCKET)
    if not bucket:
        return {}
    try:
        obj = _s3_client().get_object(Bucket=bucket, Key=_CHROMA_META_KEY)
        data = json.loads(obj["Body"].read().decode("utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        logger.debug("Chroma metadata JSON unavailable: %s", exc)
        return {}


def _s3_sync_manifest_stats() -> dict[str, Any]:
    bucket = os.getenv("AWS_S3_BUCKET", _S3_BUCKET)
    if not bucket:
        return {}
    try:
        obj = _s3_client().get_object(Bucket=bucket, Key=_MANIFEST_KEY)
        data = json.loads(obj["Body"].read().decode("utf-8"))
        if not isinstance(data, dict):
            return {}
        updated = data.get("_last_updated_count")
        return {
            "files_updated": int(updated) if updated is not None else None,
            "last_sync": _parse_iso(data.get("_last_sync")),
        }
    except Exception as exc:
        logger.debug("Sync manifest unavailable: %s", exc)
        return {}


def refresh_source_label(source: str | None) -> str:
    """Human-readable label for admin refresh panel."""
    labels = {
        "s3:chroma_last_refreshed.json": "GitHub Actions",
        "local:refresh_status.json": "Admin server",
        "s3:chroma_db/chroma_db.tar.gz": "S3 Chroma backup",
        "s3:state/sync_manifest.json": "S3 sync manifest",
        "local:chroma_db_mtime": "Local Chroma volume",
        "knowledge_base": "GitHub Actions",
    }
    if not source:
        return "Unknown"
    return labels.get(source, source.replace("s3:", "S3 · ").replace("local:", "Local · "))


def _local_refresh_status() -> tuple[str | None, str]:
    from backend.core.refresh_pipeline import get_status

    rs = get_status()
    ts = _parse_iso(rs.get("last_run"))
    if ts and rs.get("state") in {"success", "failed"}:
        return ts, "local:refresh_status.json"
    return None, ""


def _chroma_dir_mtime() -> tuple[str | None, str]:
    from backend.core.chroma_paths import chroma_persist_dir

    chroma_dir = chroma_persist_dir()
    if not chroma_dir.exists():
        return None, ""
    try:
        mtime = chroma_dir.stat().st_mtime
        return datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat(), "local:chroma_db_mtime"
    except OSError:
        return None, ""


def get_knowledge_base_last_refreshed() -> dict[str, Any]:
    """
    Return { last_refreshed, source } using the best available signal.

    Priority:
      1. state/chroma_last_refreshed.json (written by GHA upload step)
      2. data/refresh_status.json (admin panel refresh)
      3. S3 LastModified on chroma_db.tar.gz (GHA / manual upload)
      4. S3 LastModified on sync_manifest.json
      5. Local chroma_db directory mtime
    """
    ts, source = _s3_chroma_metadata()
    if ts:
        return {"last_refreshed": ts, "source": source}

    ts, source = _local_refresh_status()
    if ts:
        return {"last_refreshed": ts, "source": source}

    for key in (_CHROMA_S3_KEY, _MANIFEST_KEY):
        ts, source = _s3_head_last_modified(key)
        if ts:
            return {"last_refreshed": ts, "source": source}

    ts, source = _chroma_dir_mtime()
    if ts:
        return {"last_refreshed": ts, "source": source}

    return {"last_refreshed": None, "source": None}


def get_refresh_panel_context() -> dict[str, Any]:
    """
    Signals for the admin Data Refresh tab when the local pipeline has not run.

    Reads S3 metadata written by GHA (chroma upload + sync manifest).
    """
    kb = get_knowledge_base_last_refreshed()
    manifest = _s3_sync_manifest_stats()
    chroma_meta = _s3_chroma_metadata_record()
    source = kb.get("source")
    return {
        "last_refreshed": kb.get("last_refreshed"),
        "source": source,
        "source_label": refresh_source_label(source if source else "knowledge_base"),
        "files_updated": manifest.get("files_updated"),
        "manifest_last_sync": manifest.get("last_sync"),
        "metadata_chunk_count": chroma_meta.get("chunk_count"),
    }
