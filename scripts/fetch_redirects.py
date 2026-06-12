#!/usr/bin/env python3
"""
Download redirects.csv from each AdobeDocs GitHub repository.
These are used by exl_redirects.py to resolve stale URLs to canonical ones.

Usage:
    python scripts/fetch_redirects.py
"""

from pathlib import Path
import httpx

REPOS = {
    "analytics": "AdobeDocs/analytics.en",
    "cja":       "AdobeDocs/analytics-platform.en",
    "aep":       "AdobeDocs/experience-platform.en",
    "ajo":       "AdobeDocs/journey-optimizer.en",
}

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)


def main() -> None:
    for product, repo in REPOS.items():
        url = f"https://raw.githubusercontent.com/{repo}/main/redirects.csv"
        print(f"Fetching {product} ({repo})...")
        try:
            resp = httpx.get(url, timeout=30, follow_redirects=True)
            if resp.status_code == 200:
                path = DATA_DIR / f"redirects-{product}.csv"
                path.write_text(resp.text, encoding="utf-8")
                lines = resp.text.strip().split("\n")
                print(f"  ✓ {len(lines) - 1} redirect entries → {path.name}")
            else:
                print(f"  ✗ HTTP {resp.status_code} — no redirects.csv in this repo")
        except Exception as exc:
            print(f"  ✗ Error: {exc}")


if __name__ == "__main__":
    main()
