"""
Data refresh pipeline — runs in background when triggered from admin panel.

Steps:
  1. Sync changed docs from AdobeDocs GitHub → S3
  2. Re-ingest changed files into ChromaDB
  3. Re-run media enrichment
  4. Upload updated ChromaDB to S3 (for Railway cold starts)

Status is written to data/refresh_status.json so the admin panel can poll it.
"""

import json
import logging
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from backend.core.knowledge_base_refresh import refresh_source_label

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).parent.parent.parent
STATUS_FILE = _ROOT / "data" / "refresh_status.json"

_lock = threading.Lock()
_running = False


def get_status() -> dict:
    if STATUS_FILE.exists():
        try:
            return json.loads(STATUS_FILE.read_text())
        except Exception:
            pass
    return {
        "state": "idle",
        "last_run": None,
        "last_run_duration_s": None,
        "files_updated": 0,
        "chunks_indexed": 0,
        "error": None,
        "log": [],
    }


def enrich_status_for_admin(
    status: dict,
    *,
    chroma_count: Optional[int] = None,
    kb_last_refreshed: Optional[str] = None,
    kb_source: Optional[str] = None,
    kb_source_label: Optional[str] = None,
    manifest_files_updated: Optional[int] = None,
) -> dict:
    """
    Fill gaps when production refreshes via GHA/S3 rather than the local pipeline.

    Railway often has no data/refresh_status.json; last_run and chunk count should
    still reflect the live knowledge base.
    """
    enriched = dict(status)
    if not enriched.get("last_run") and kb_last_refreshed:
        enriched["last_run"] = kb_last_refreshed
        enriched["last_run_source"] = kb_source or "knowledge_base"
    if kb_source_label:
        enriched["last_run_source_label"] = kb_source_label
    if not enriched.get("chunks_indexed") and chroma_count:
        enriched["chunks_indexed"] = chroma_count
    if not enriched.get("files_updated") and manifest_files_updated is not None:
        enriched["files_updated"] = manifest_files_updated

    if not enriched.get("log") and kb_last_refreshed:
        label = kb_source_label or refresh_source_label(kb_source)
        lines = [
            f"Completed: {kb_last_refreshed}",
            f"Source: {label}",
        ]
        if chroma_count:
            lines.append(f"ChromaDB chunks: {chroma_count:,}")
        if manifest_files_updated is not None:
            if manifest_files_updated == 0:
                lines.append("Docs updated in last sync: 0 (no file changes)")
            else:
                lines.append(f"Docs updated in last sync: {manifest_files_updated:,}")
        if enriched.get("last_run_duration_s"):
            lines.append(f"Duration: {enriched['last_run_duration_s']}s")
        else:
            lines.append("Duration: n/a (scheduled GitHub Actions run)")
        enriched["log"] = lines

    return enriched


def _write_status(status: dict) -> None:
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(json.dumps(status, indent=2))


def _run_script(script: str, args: list[str], status: dict, log: list) -> bool:
    """Run a script as subprocess, stream output to log list."""
    cmd = [sys.executable, str(_ROOT / "scripts" / script)] + args
    log.append(f"▶ Running {script}...")
    _write_status(status)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(_ROOT),
            timeout=3600,
        )
        lines = (result.stdout + result.stderr).strip().splitlines()
        for line in lines[-20:]:       # keep last 20 lines per script
            log.append(line)
        _write_status(status)

        if result.returncode != 0:
            log.append(f"✗ {script} exited with code {result.returncode}")
            return False
        log.append(f"✓ {script} completed")
        return True
    except subprocess.TimeoutExpired:
        log.append(f"✗ {script} timed out after 1 hour")
        return False
    except Exception as e:
        log.append(f"✗ {script} failed: {e}")
        return False


def _run_refresh(force: bool = False):
    global _running
    status = get_status()
    log: list[str] = []
    started = datetime.now(timezone.utc)

    status.update({
        "state": "running",
        "started_at": started.isoformat(),
        "log": log,
        "error": None,
    })
    _write_status(status)

    try:
        # Step 1: Sync from GitHub → S3
        log.append("=== Step 1: Sync GitHub → S3 ===")
        sync_args = ["--force"] if force else []
        if not _run_script("sync_docs_to_s3.py", sync_args, status, log):
            raise RuntimeError("Sync failed")

        # Read how many files were updated
        from scripts.sync_docs_to_s3 import _load_manifest
        manifest = _load_manifest()
        files_updated = manifest.get("_last_updated_count", 0)
        status["files_updated"] = files_updated

        if files_updated == 0 and not force:
            log.append("✓ No files changed — skipping ingest")
        else:
            # Step 2: Re-ingest into ChromaDB
            log.append("=== Step 2: Ingest into ChromaDB ===")
            if not _run_script("ingest_to_chroma.py", [], status, log):
                raise RuntimeError("Ingest failed")

            # Step 3: Media enrichment
            log.append("=== Step 3: Media enrichment ===")
            if not _run_script("ingest_with_media.py", [], status, log):
                log.append("⚠ Media enrichment failed — continuing")

            # Step 4: Upload ChromaDB to S3
            log.append("=== Step 4: Upload ChromaDB → S3 ===")
            if not _run_script("upload_chroma_to_s3.py", [], status, log):
                log.append("⚠ ChromaDB upload failed — local DB updated but S3 backup failed")

        # Get final chunk count
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings
            client = chromadb.PersistentClient(
                path=str(_ROOT / "chroma_db"),
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            col = client.get_collection("experience_league")
            status["chunks_indexed"] = col.count()
        except Exception:
            pass

        duration = (datetime.now(timezone.utc) - started).total_seconds()
        status.update({
            "state": "success",
            "last_run": started.isoformat(),
            "last_run_duration_s": round(duration),
            "log": log[-50:],      # keep last 50 log lines
        })
        log.append(f"✅ Refresh complete in {round(duration)}s")
        logger.info(f"Refresh complete: {files_updated} files updated, {status['chunks_indexed']} chunks")

    except Exception as e:
        duration = (datetime.now(timezone.utc) - started).total_seconds()
        status.update({
            "state": "failed",
            "last_run": started.isoformat(),
            "last_run_duration_s": round(duration),
            "error": str(e),
            "log": log[-50:],
        })
        logger.exception("Refresh failed")
    finally:
        _write_status(status)
        with _lock:
            _running = False


def trigger_refresh(force: bool = False) -> dict:
    """Start a background refresh. Returns immediately with current status."""
    global _running
    with _lock:
        if _running:
            return {"started": False, "reason": "Refresh already running"}
        _running = True

    thread = threading.Thread(target=_run_refresh, args=(force,), daemon=True)
    thread.start()
    return {"started": True}
