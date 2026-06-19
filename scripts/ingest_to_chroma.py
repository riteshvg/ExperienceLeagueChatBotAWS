#!/usr/bin/env python3
"""
Ingest Adobe Experience League documents from S3 into ChromaDB.

Usage:
    python scripts/ingest_to_chroma.py
    python scripts/ingest_to_chroma.py --limit 50
    python scripts/ingest_to_chroma.py --product "Adobe Analytics"
    python scripts/ingest_to_chroma.py --reset   # drop & re-create collection

The script reads data/metadata_registry.json to get the list of S3 keys,
downloads each markdown file from S3, splits it into ≤500-token chunks,
embeds them with sentence-transformers, and upserts into ChromaDB.
"""

import argparse
import json
import logging
import os
import random
import re
import sys
import time
from pathlib import Path
from typing import Optional

import boto3
import chromadb
from botocore.exceptions import ClientError
from chromadb.config import Settings as ChromaSettings

# ── project root ─────────────────────────────────────────────────────────────
_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))

from src.utils.citation_metadata import build_index_metadata, metadata_to_chroma_fields

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
REGISTRY_PATH = _ROOT / "data" / "metadata_registry.json"
CHANGED_KEYS_PATH = _ROOT / "data" / "changed_s3_keys.txt"
CHROMA_DIR = _ROOT / "chroma_db"
COLLECTION_NAME = "experience_league"
TITAN_MODEL_ID = "amazon.titan-embed-text-v2:0"
CHUNK_SIZE = 500        # approximate token ceiling per chunk
CHUNK_OVERLAP = 50      # tokens of overlap between consecutive chunks
BATCH_SIZE = 64         # ChromaDB upsert batch size
EMBED_MAX_ATTEMPTS = 8
EMBED_RETRY_BASE_S = 2
EMBED_RETRY_MAX_S = 60
RETRIABLE_BEDROCK_ERRORS = frozenset({
    "ModelErrorException",
    "ThrottlingException",
    "ServiceUnavailableException",
    "ServiceUnavailable",
    "ModelTimeoutException",
    "InternalServerException",
    "TooManyRequestsException",
})


# ── Chunking ─────────────────────────────────────────────────────────────────

def _rough_token_count(text: str) -> int:
    """Approximate tokens (4 chars ≈ 1 token)."""
    return len(text) // 4


def split_markdown(text: str, s3_key: str) -> list[str]:
    """
    Split a markdown document into chunks of ~CHUNK_SIZE tokens.

    Strategy:
    1. Split on top-level headers (## / ###).
    2. If a section is still too large, split on paragraphs.
    3. If a paragraph is still too large, hard-split by character count.
    """
    # Normalise line endings
    text = text.replace("\r\n", "\n").strip()

    # Split on ## or ### headers (keep the header line with its section)
    sections = re.split(r"(?m)^(#{1,3} .+)$", text)

    # re.split with a capturing group interleaves headers and bodies
    chunks: list[str] = []
    current = ""

    i = 0
    while i < len(sections):
        part = sections[i].strip()
        if not part:
            i += 1
            continue

        candidate = (current + "\n\n" + part).strip() if current else part

        if _rough_token_count(candidate) <= CHUNK_SIZE:
            current = candidate
        else:
            if current:
                chunks.append(current)
            # Part itself might be large — split by paragraphs
            paragraphs = [p.strip() for p in part.split("\n\n") if p.strip()]
            para_buf = ""
            for para in paragraphs:
                c2 = (para_buf + "\n\n" + para).strip() if para_buf else para
                if _rough_token_count(c2) <= CHUNK_SIZE:
                    para_buf = c2
                else:
                    if para_buf:
                        chunks.append(para_buf)
                    # Hard-split oversized paragraph
                    chars = CHUNK_SIZE * 4
                    overlap = CHUNK_OVERLAP * 4
                    for start in range(0, len(para), chars - overlap):
                        chunks.append(para[start : start + chars])
                    para_buf = ""
            current = para_buf
        i += 1

    if current:
        chunks.append(current)

    # Filter blanks
    return [c for c in chunks if c.strip()]


# ── S3 helpers ────────────────────────────────────────────────────────────────

def download_s3_object(s3_client, bucket: str, key: str) -> Optional[str]:
    try:
        resp = s3_client.get_object(Bucket=bucket, Key=key)
        content = resp["Body"].read()
        return content.decode("utf-8", errors="replace")
    except s3_client.exceptions.NoSuchKey:
        logger.debug(f"Key not found: s3://{bucket}/{key}")
        return None
    except Exception as exc:
        logger.warning(f"Could not download s3://{bucket}/{key}: {exc}")
        return None


def _load_existing_ids(collection) -> set[str]:
    """Paginate Chroma get() to collect all chunk IDs."""
    existing: set[str] = set()
    offset = 0
    page_size = 1000
    while True:
        data = collection.get(limit=page_size, offset=offset, include=[])
        ids = data.get("ids") or []
        if not ids:
            break
        existing.update(ids)
        offset += len(ids)
        if len(ids) < page_size:
            break
    return existing


def _embed_with_retry(bedrock, text: str) -> list[float]:
    body = json.dumps({"inputText": text[:8000], "dimensions": 1024, "normalize": True})
    for attempt in range(1, EMBED_MAX_ATTEMPTS + 1):
        try:
            resp = bedrock.invoke_model(
                modelId=TITAN_MODEL_ID,
                body=body,
                contentType="application/json",
                accept="application/json",
            )
            return json.loads(resp["body"].read())["embedding"]
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code in RETRIABLE_BEDROCK_ERRORS and attempt < EMBED_MAX_ATTEMPTS:
                delay = min(
                    EMBED_RETRY_MAX_S,
                    EMBED_RETRY_BASE_S ** attempt + random.uniform(0, 1),
                )
                logger.warning(
                    "Bedrock embed failed (%s) — retry %d/%d in %.1fs",
                    code,
                    attempt,
                    EMBED_MAX_ATTEMPTS,
                    delay,
                )
                time.sleep(delay)
                continue
            raise


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Ingest docs into ChromaDB")
    parser.add_argument("--limit", type=int, default=0, help="Max documents to process (0 = all)")
    parser.add_argument("--product", type=str, default="", help="Filter by product name substring")
    parser.add_argument(
        "--prefix",
        action="append",
        default=[],
        help="S3 key substring filter — repeat for multiple folders (e.g. --prefix help/ingestion/)",
    )
    parser.add_argument("--reset", action="store_true", help="Drop and re-create ChromaDB collection")
    parser.add_argument(
        "--changed-only", action="store_true",
        help=f"Only ingest keys listed in {CHANGED_KEYS_PATH} (written by sync_docs_to_s3.py). "
             "Falls back to full ingest if the file is missing or empty.",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip chunks whose IDs already exist in ChromaDB (resume / avoid re-embedding).",
    )
    parser.add_argument(
        "--start-at",
        type=int,
        default=0,
        help="Skip the first N registry entries (resume after an interrupted ingest).",
    )
    args = parser.parse_args()

    # ── Load metadata registry ─────────────────────────────────────────────
    if not REGISTRY_PATH.exists():
        logger.error(f"Registry not found: {REGISTRY_PATH}")
        sys.exit(1)

    with open(REGISTRY_PATH) as f:
        registry: dict = json.load(f)

    logger.info(f"Loaded registry: {len(registry)} entries")

    # Filter to only changed keys if --changed-only and the file exists with content
    entries = list(registry.items())
    if args.changed_only:
        if CHANGED_KEYS_PATH.exists():
            changed_keys = {
                line.strip() for line in CHANGED_KEYS_PATH.read_text().splitlines() if line.strip()
            }
            if changed_keys:
                entries = [(k, v) for k, v in entries if k in changed_keys]
                logger.info(f"--changed-only: {len(entries)} entries to re-ingest "
                            f"({len(changed_keys)} changed keys from {CHANGED_KEYS_PATH.name})")
            else:
                logger.info("--changed-only: changed_s3_keys.txt is empty — nothing to ingest")
                entries = []
        else:
            logger.warning(f"--changed-only set but {CHANGED_KEYS_PATH} not found — ingesting all")

    # Filter by product if requested
    if args.product:
        entries = [
            (k, v) for k, v in entries
            if args.product.lower() in v.get("product", "").lower()
        ]
        logger.info(f"Filtered to {len(entries)} entries matching product='{args.product}'")

    if args.prefix:
        entries = [
            (k, v) for k, v in entries
            if any(p in k for p in args.prefix)
        ]
        logger.info(
            f"Filtered to {len(entries)} entries matching prefix(es): {args.prefix}"
        )

    if args.limit > 0:
        entries = entries[: args.limit]
        logger.info(f"Limiting to {len(entries)} entries")

    total_entries = len(entries)
    start_offset = max(args.start_at, 0)
    if start_offset > 0:
        if start_offset >= total_entries:
            logger.info("--start-at %d >= entry count — nothing to ingest", start_offset)
            return
        logger.info(
            "Resuming ingest at registry index %d/%d (skipping first %d entries)",
            start_offset,
            total_entries,
            start_offset,
        )
        entries = entries[start_offset:]

    # ── AWS S3 client ──────────────────────────────────────────────────────
    bucket = os.getenv("AWS_S3_BUCKET", "")
    if not bucket:
        logger.error("AWS_S3_BUCKET env var not set")
        sys.exit(1)

    s3 = boto3.client(
        "s3",
        region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )

    # ── ChromaDB client ────────────────────────────────────────────────────
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    chroma_client = chromadb.PersistentClient(
        path=str(CHROMA_DIR),
        settings=ChromaSettings(anonymized_telemetry=False),
    )

    if args.reset:
        try:
            chroma_client.delete_collection(COLLECTION_NAME)
            logger.info(f"Dropped collection '{COLLECTION_NAME}'")
        except Exception:
            pass

    collection = chroma_client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    logger.info(f"Collection '{COLLECTION_NAME}' has {collection.count()} existing chunks")

    existing_ids: set[str] = set()
    if args.skip_existing:
        logger.info("Loading existing chunk IDs for --skip-existing…")
        existing_ids = _load_existing_ids(collection)
        logger.info("Found %d existing chunks — will skip re-embedding those", len(existing_ids))

    # ── Bedrock client for Titan embeddings ───────────────────────────────
    logger.info(f"Using Titan Embed v2 via Bedrock for embeddings…")
    bedrock = boto3.client(
        "bedrock-runtime",
        region_name=os.getenv("BEDROCK_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1")),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )

    embed = lambda text: _embed_with_retry(bedrock, text)

    # ── Ingest loop ────────────────────────────────────────────────────────
    ids_batch: list[str] = []
    docs_batch: list[str] = []
    embeddings_batch: list[list[float]] = []
    metas_batch: list[dict] = []

    total_chunks = 0
    skipped = 0
    skipped_existing = 0
    t0 = time.time()

    for doc_idx, (s3_key, meta) in enumerate(entries):
        abs_idx = start_offset + doc_idx
        if doc_idx % 50 == 0:
            elapsed = time.time() - t0
            logger.info(
                f"[{abs_idx}/{total_entries}] "
                f"chunks={total_chunks}  skipped={skipped}  "
                f"skipped_existing={skipped_existing}  "
                f"elapsed={elapsed:.0f}s"
            )

        text = download_s3_object(s3, bucket, s3_key)
        if not text:
            skipped += 1
            continue

        chunks = split_markdown(text, s3_key)
        if not chunks:
            skipped += 1
            continue

        for chunk_idx, chunk in enumerate(chunks):
            chunk_id = f"{s3_key}#{chunk_idx}"
            if chunk_id in existing_ids:
                skipped_existing += 1
                continue

            embedding = embed(chunk)

            citation = build_index_metadata(s3_key)
            citation_fields = metadata_to_chroma_fields(citation)

            ids_batch.append(chunk_id)
            docs_batch.append(chunk)
            embeddings_batch.append(embedding)
            metas_batch.append(
                {
                    "s3_key": s3_key,
                    "chunk_index": chunk_idx,
                    "title": meta.get("title", ""),
                    "product": meta.get("product", ""),
                    "doc_type": meta.get("doc_type", ""),
                    "level": meta.get("level", ""),
                    **citation_fields,
                }
            )
            total_chunks += 1

            # Flush batch
            if len(ids_batch) >= BATCH_SIZE:
                collection.upsert(
                    ids=ids_batch,
                    documents=docs_batch,
                    embeddings=embeddings_batch,
                    metadatas=metas_batch,
                )
                ids_batch, docs_batch, embeddings_batch, metas_batch = [], [], [], []

    # Final flush
    if ids_batch:
        collection.upsert(
            ids=ids_batch,
            documents=docs_batch,
            embeddings=embeddings_batch,
            metadatas=metas_batch,
        )

    elapsed = time.time() - t0
    logger.info(
        f"Done — {total_chunks} chunks from {len(entries) - skipped} documents "
        f"({skipped} skipped, {skipped_existing} existing) in {elapsed:.1f}s"
    )
    logger.info(f"Collection now has {collection.count()} total chunks")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(_ROOT / ".env")
    main()
