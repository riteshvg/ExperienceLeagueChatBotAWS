#!/usr/bin/env python3
"""
Validate canonical Experience League URLs for indexed documentation.

Reports one row per unique source document (s3_key):
  product | repo | repo_path | exl_url | status

status: live | dead | unmapped

Usage:
    python3 scripts/validate_exl_urls.py
    python3 scripts/validate_exl_urls.py --product "Adobe Journey Optimizer"
    python3 scripts/validate_exl_urls.py --csv reports/exl_validation.csv
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import sys
from collections import defaultdict
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))

from src.utils.citation_metadata import ValidationRow, validate_urls, validation_row

CHROMA_PATH = _ROOT / "chroma_db"
COLLECTION = "experience_league"


async def run(product_filter: str | None, csv_path: Path | None) -> int:
    col = chromadb.PersistentClient(
        path=str(CHROMA_PATH),
        settings=ChromaSettings(anonymized_telemetry=False),
    ).get_collection(COLLECTION)

    pages: dict[str, dict] = {}
    for meta in col.get(include=["metadatas"])["metadatas"]:
        sk = meta.get("s3_key", "")
        if not sk or sk in pages:
            continue
        if product_filter and meta.get("product") != product_filter:
            continue
        pages[sk] = meta

    from src.utils.exl_url_mapper import derive_exl_url, is_specific_url

    derive_candidates = [
        derive_exl_url(sk) for sk in pages if is_specific_url(derive_exl_url(sk))
    ]
    live_map = await validate_urls(derive_candidates)

    rows: list[ValidationRow] = []
    for sk, meta in sorted(pages.items()):
        rows.append(validation_row(sk, meta.get("product", ""), live_map))

    stats: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in rows:
        stats[row.product][row.status] += 1

    print("=== EXL URL validation report ===")
    print(f"Unique documents: {len(rows)}")
    print()
    for product in sorted(stats):
        s = stats[product]
        print(
            f"  {product:35s}  live={s.get('live', 0):4d}  "
            f"dead={s.get('dead', 0):4d}  unmapped={s.get('unmapped', 0):4d}"
        )

    if csv_path:
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["product", "repo", "repo_path", "exl_url", "status"])
            for row in rows:
                writer.writerow([row.product, row.repo, row.repo_path, row.exl_url, row.status])
        print(f"\nWrote {csv_path}")

    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--product", help="Filter to a single product name")
    parser.add_argument("--csv", type=Path, help="Optional CSV output path")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(args.product, args.csv)))


if __name__ == "__main__":
    main()
