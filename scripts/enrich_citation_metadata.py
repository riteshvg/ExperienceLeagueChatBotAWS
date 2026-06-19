#!/usr/bin/env python3
"""Enrich ChromaDB with index-time citation metadata. See module docstring in enrich script."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))

CHANGED_KEYS_PATH = _ROOT / "data" / "changed_s3_keys.txt"

from src.utils.chroma_citation_enrich import enrich_chroma_collection

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Enrich Chroma citation metadata for all Adobe solutions")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--product", help="Limit to one product")
    parser.add_argument(
        "--prefix",
        help="Limit to s3_key substring (e.g. adobe-docs/customer-journey-analytics/help/cja-main)",
    )
    parser.add_argument("--skip-validate", action="store_true")
    parser.add_argument(
        "--changed-only",
        action="store_true",
        help=f"Only enrich chunks whose s3_key appears in {CHANGED_KEYS_PATH.name}",
    )
    args = parser.parse_args()

    changed_keys: set[str] | None = None
    if args.changed_only and CHANGED_KEYS_PATH.exists():
        changed_keys = {
            line.strip() for line in CHANGED_KEYS_PATH.read_text().splitlines() if line.strip()
        }
        if not changed_keys:
            logging.info("No changed keys — nothing to enrich")
            return

    asyncio.run(
        enrich_chroma_collection(
            dry_run=args.dry_run,
            product_filter=args.product,
            prefix_filter=args.prefix,
            skip_validate=args.skip_validate,
            changed_s3_keys=changed_keys,
        )
    )


if __name__ == "__main__":
    main()
