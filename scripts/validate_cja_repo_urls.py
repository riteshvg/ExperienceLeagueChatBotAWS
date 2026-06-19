#!/usr/bin/env python3
"""
Validate derived EXL URLs for CJA main-guide repo paths.

Reads repo paths from reports/exl_validation.csv (or --csv) and HTTP-checks
each derived URL after exl_url_mapper + redirect resolution.

Usage:
    python3 scripts/validate_cja_repo_urls.py
    python3 scripts/validate_cja_repo_urls.py --csv reports/exl_validation.csv
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import sys
from pathlib import Path

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))

from src.utils.citation_metadata import validate_urls
from src.utils.exl_url_mapper import derive_exl_url, is_specific_url

DEFAULT_CSV = _ROOT / "reports" / "exl_validation.csv"


async def run(csv_path: Path) -> int:
    if not csv_path.exists():
        print(f"CSV not found: {csv_path}", file=sys.stderr)
        return 1

    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("product") != "Customer Journey Analytics":
                continue
            if "analytics-platform.en" not in row.get("repo", ""):
                continue
            rows.append(row)

    candidates: list[tuple[str, str | None]] = []
    for row in rows:
        s3_key = f"adobe-docs/customer-journey-analytics/{row['repo_path']}"
        derived = derive_exl_url(s3_key)
        candidates.append((row["repo_path"], derived))

    urls = [u for _, u in candidates if is_specific_url(u)]
    live_map = await validate_urls(urls)

    live = dead = unmapped = 0
    print("=== CJA repo path → derived EXL URL validation ===")
    print(f"Paths checked: {len(candidates)}\n")
    for repo_path, derived in sorted(candidates, key=lambda x: x[0]):
        if not is_specific_url(derived):
            status = "unmapped"
            unmapped += 1
        elif live_map.get(derived, False):
            status = "live"
            live += 1
        else:
            status = "dead"
            dead += 1
        print(f"  [{status:8s}] {repo_path[:70]}")
        if derived:
            print(f"             → {derived[:90]}")

    print(f"\nSummary: live={live} dead={dead} unmapped={unmapped} (total={len(candidates)})")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(args.csv)))


if __name__ == "__main__":
    main()
