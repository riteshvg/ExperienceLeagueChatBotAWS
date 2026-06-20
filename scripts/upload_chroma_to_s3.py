#!/usr/bin/env python3
"""
Compress chroma_db/ and upload to S3 as chroma_db.tar.gz.

Run once locally whenever you want to refresh the production database:
    python scripts/upload_chroma_to_s3.py

Railway downloads this archive on first startup if chroma_db/ is empty.
Set FORCE_CHROMA_RESTORE=true on Railway to wipe the volume and re-download.

Before a FORCE redeploy, set on Railway (optional but recommended for user messaging):
  KNOWLEDGE_BANK_UPDATING=true
  KNOWLEDGE_BANK_UPDATE_STARTED_AT=<ISO-8601 UTC, e.g. 2026-06-19T10:00:00Z>
  CHROMA_RESTORE_ETA_MINUTES=4   (default — shown in the "check back at" message)
After /api/health shows expected chunk count, unset KNOWLEDGE_BANK_UPDATING and FORCE.
"""

import json
import os
import sys
import tarfile
import tempfile
import logging
from datetime import datetime, timezone
from pathlib import Path

import boto3
from dotenv import load_dotenv

_ROOT = Path(__file__).parent.parent
load_dotenv(_ROOT / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s")
logger = logging.getLogger(__name__)

CHROMA_DIR = _ROOT / "chroma_db"
S3_BUCKET   = os.getenv("AWS_S3_BUCKET", "experienceleaguechatbot")
S3_KEY      = "chroma_db/chroma_db.tar.gz"


def main():
    if not CHROMA_DIR.exists():
        logger.error(f"chroma_db/ not found at {CHROMA_DIR}")
        sys.exit(1)

    s3 = boto3.client(
        "s3",
        region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
    )

    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
        tmp_path = tmp.name

    logger.info(f"Compressing {CHROMA_DIR} → {tmp_path} ...")
    with tarfile.open(tmp_path, "w:gz") as tar:
        tar.add(CHROMA_DIR, arcname="chroma_db")

    size_mb = Path(tmp_path).stat().st_size / 1024 / 1024
    logger.info(f"Compressed size: {size_mb:.1f} MB")

    logger.info(f"Uploading to s3://{S3_BUCKET}/{S3_KEY} ...")
    s3.upload_file(
        tmp_path,
        S3_BUCKET,
        S3_KEY,
        ExtraArgs={"ContentType": "application/gzip"},
        Callback=lambda b: print(f"\r  Uploaded {b/1024/1024:.1f} MB", end="", flush=True),
    )
    print()

    Path(tmp_path).unlink()

    uploaded_at = datetime.now(timezone.utc).isoformat()
    chunk_count = 0
    try:
        import chromadb
        from chromadb.config import Settings as ChromaSettings
        client = chromadb.PersistentClient(
            path=str(CHROMA_DIR),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        chunk_count = client.get_collection("experience_league").count()
    except Exception as exc:
        logger.warning("Could not read chunk count for metadata: %s", exc)

    meta_key = "state/chroma_last_refreshed.json"
    meta_body = json.dumps(
        {
            "uploaded_at": uploaded_at,
            "chunk_count": chunk_count,
            "s3_key": S3_KEY,
        },
        indent=2,
    )
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=meta_key,
        Body=meta_body.encode("utf-8"),
        ContentType="application/json",
    )
    logger.info("Wrote %s (uploaded_at=%s, chunks=%s)", meta_key, uploaded_at, chunk_count)

    logger.info("Done ✓")
    logger.info(f"Railway will download from s3://{S3_BUCKET}/{S3_KEY} on next cold start")


if __name__ == "__main__":
    main()
