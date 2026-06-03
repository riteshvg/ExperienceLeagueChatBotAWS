#!/usr/bin/env python3
"""
Compress chroma_db/ and upload to S3 as chroma_db.tar.gz.

Run once locally whenever you want to refresh the production database:
    python scripts/upload_chroma_to_s3.py

Railway downloads this archive on first startup if chroma_db/ is empty.
"""

import os
import sys
import tarfile
import tempfile
import logging
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
    logger.info("Done ✓")
    logger.info(f"Railway will download from s3://{S3_BUCKET}/{S3_KEY} on next cold start")


if __name__ == "__main__":
    main()
