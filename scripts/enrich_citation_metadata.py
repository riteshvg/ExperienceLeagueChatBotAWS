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

from src.utils.chroma_citation_enrich import enrich_chroma_collection

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Enrich Chroma citation metadata for all Adobe solutions")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--product", help="Limit to one product")
    parser.add_argument("--skip-validate", action="store_true")
    args = parser.parse_args()
    asyncio.run(
        enrich_chroma_collection(
            dry_run=args.dry_run,
            product_filter=args.product,
            skip_validate=args.skip_validate,
        )
    )


if __name__ == "__main__":
    main()
