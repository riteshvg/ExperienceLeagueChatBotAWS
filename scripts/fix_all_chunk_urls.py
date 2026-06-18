#!/usr/bin/env python3
"""Backward-compatible alias for enrich_citation_metadata.py."""

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
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(enrich_chroma_collection(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
