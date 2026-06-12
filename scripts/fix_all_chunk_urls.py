#!/usr/bin/env python3
"""
One-time (idempotent) ChromaDB URL fix.

For every chunk in the collection, derives the canonical Experience League URL
from its s3_key and updates the `url` and `url_source` metadata fields if the
derived URL is better than what's currently stored.

Usage:
    venv/bin/python3.12 scripts/fix_all_chunk_urls.py [--dry-run]

After running:
    venv/bin/python3.12 scripts/upload_chroma_to_s3.py
    railway up
"""

import argparse
import logging
import sys
from collections import defaultdict
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))

from src.utils.exl_url_mapper import derive_exl_url, is_specific_url

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

CHROMA_PATH = _ROOT / "chroma_db"
COLLECTION_NAME = "experience_league"
BATCH_SIZE = 500


def main(dry_run: bool = False) -> None:
    client = chromadb.PersistentClient(
        path=str(CHROMA_PATH),
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    col = client.get_collection(COLLECTION_NAME)

    logger.info("Loading all chunks from ChromaDB…")
    data = col.get(include=["metadatas"])
    ids: list[str] = data["ids"]
    metas: list[dict] = data["metadatas"]
    logger.info(f"Loaded {len(ids)} chunks")

    # Counters per product
    updated: dict[str, int] = defaultdict(int)
    already_correct: dict[str, int] = defaultdict(int)
    no_mapping: dict[str, int] = defaultdict(int)

    ids_to_fix: list[str] = []
    metas_to_fix: list[dict] = []

    for doc_id, meta in zip(ids, metas):
        s3_key = meta.get("s3_key", "")
        product = meta.get("product", "unknown")
        current_url = meta.get("url", "")

        derived = derive_exl_url(s3_key) if s3_key else None

        if not is_specific_url(derived):
            no_mapping[product] += 1
            continue

        if derived == current_url:
            already_correct[product] += 1
            continue

        # Derived is better — queue an update
        new_meta = dict(meta)
        new_meta["url"] = derived
        new_meta["url_source"] = "derived"
        ids_to_fix.append(doc_id)
        metas_to_fix.append(new_meta)
        updated[product] += 1

    logger.info(f"\nSummary:")
    logger.info(f"  Total chunks:     {len(ids)}")
    logger.info(f"  To update:        {len(ids_to_fix)}")
    logger.info(f"  Already correct:  {sum(already_correct.values())}")
    logger.info(f"  No mapping found: {sum(no_mapping.values())}")

    logger.info(f"\nUpdates per product:")
    for prod in sorted(set(list(updated) + list(already_correct) + list(no_mapping))):
        u = updated.get(prod, 0)
        a = already_correct.get(prod, 0)
        n = no_mapping.get(prod, 0)
        logger.info(f"  {prod:40s}  updated={u:5d}  correct={a:5d}  no-map={n:5d}")

    if not ids_to_fix:
        logger.info("\nNothing to fix — all chunks already have canonical URLs.")
        return

    if dry_run:
        logger.info(f"\n[DRY RUN] Would update {len(ids_to_fix)} chunks. Pass without --dry-run to apply.")
        # Print 10 examples
        for doc_id, meta in zip(ids_to_fix[:10], metas_to_fix[:10]):
            old = next((m.get("url","") for m in metas if m.get("s3_key") == meta.get("s3_key")), "")
            logger.info(f"  {meta['s3_key']}")
            logger.info(f"    before: {old}")
            logger.info(f"    after:  {meta['url']}")
        return

    logger.info(f"\nApplying {len(ids_to_fix)} updates in batches of {BATCH_SIZE}…")
    for start in range(0, len(ids_to_fix), BATCH_SIZE):
        batch_ids = ids_to_fix[start:start + BATCH_SIZE]
        batch_metas = metas_to_fix[start:start + BATCH_SIZE]
        col.update(ids=batch_ids, metadatas=batch_metas)
        logger.info(f"  Updated {min(start + BATCH_SIZE, len(ids_to_fix))}/{len(ids_to_fix)}")

    logger.info("\nDone. Next steps:")
    logger.info("  venv/bin/python3.12 scripts/upload_chroma_to_s3.py")
    logger.info("  railway up   (or push to GitHub for auto-deploy)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Report what would change without writing to ChromaDB")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
