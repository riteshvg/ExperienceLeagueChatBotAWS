"""
Loads Adobe's redirects.csv files and resolves stale Experience League URLs
to their current canonical destinations.

CSV format:
  source,destination
  /docs/analytics/.../freeform-table.html,/docs/analytics/.../freeform-table/freeform-table.html

Both columns use /docs/ prefix and .html suffix.
Experience League URLs use neither — normalisation required to match.
"""

import csv
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EXL_BASE = "https://experienceleague.adobe.com/en"

REDIRECTS_FILES = [
    DATA_DIR / "redirects-analytics.csv",
    DATA_DIR / "redirects-cja.csv",
    DATA_DIR / "redirects-aep.csv",
    DATA_DIR / "redirects-ajo.csv",
]


def _normalise(path: str) -> str:
    """Strip /docs/ prefix, .html suffix, leading and trailing slashes."""
    path = path.strip()
    for prefix in ("/docs/", "docs/"):
        if path.startswith(prefix):
            path = path[len(prefix):]
            break
    path = path.lstrip("/").rstrip("/")
    if path.endswith(".html"):
        path = path[:-5]
    return path


@lru_cache(maxsize=1)
def _load_redirects() -> dict[str, str]:
    """Load all redirects CSV files into a combined normalised dict."""
    redirects: dict[str, str] = {}
    for csv_path in REDIRECTS_FILES:
        if not csv_path.exists():
            continue
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                src = _normalise(row.get("source", ""))
                dst = row.get("destination", "").strip()
                if not src or not dst:
                    continue
                if dst.startswith("http"):
                    redirects[src] = dst
                else:
                    redirects[src] = f"{EXL_BASE}/docs/{_normalise(dst)}"
    return redirects


def resolve_canonical_url(exl_url: str) -> str:
    """
    Given an Experience League URL, return the canonical current URL.
    If the URL appears as a source in any redirects CSV, return the destination.
    Otherwise return the URL unchanged.
    """
    redirects = _load_redirects()
    path = exl_url.replace(f"{EXL_BASE}/docs/", "").replace(
        "https://experienceleague.adobe.com/docs/", ""
    )
    path = _normalise(path)
    return redirects.get(path, exl_url)
