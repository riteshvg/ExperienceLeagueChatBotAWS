#!/usr/bin/env python3
"""
Build CJA repo_path → Experience League URL mapping from TOC files and EXL discovery.

1. Parse TOC.md files from GitHub (when available) under help/cja-main/
2. Collect live EXL URLs from redirects.csv destinations + link crawl from seed pages
3. For each repo path: use derive_exl_url, then slug-match against EXL catalog if dead
4. HTTP-validate and write reports/cja_toc_exl_mapping.csv
5. Write data/cja_toc_exl_overrides.json (live mappings only) for exl_url_mapper

Usage:
    python3 scripts/build_cja_toc_exl_mapping.py
    python3 scripts/build_cja_toc_exl_mapping.py --paths-csv reports/exl_validation.csv
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import httpx
import requests

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))

from scripts.extract_metadata_from_github import parse_toc_file  # noqa: E402
from src.utils.citation_metadata import validate_urls  # noqa: E402
from src.utils.exl_redirects import _load_redirects, _normalise  # noqa: E402
from src.utils.exl_url_mapper import derive_exl_url, is_specific_url  # noqa: E402

GITHUB = "AdobeDocs/analytics-platform.en"
BRANCH = "main"
RAW = f"https://raw.githubusercontent.com/{GITHUB}/{BRANCH}"
S3_PREFIX = "adobe-docs/customer-journey-analytics/"
EXL_SEEDS = [
    "https://experienceleague.adobe.com/en/docs/analytics-platform/using/cja-workspace/home",
    "https://experienceleague.adobe.com/en/docs/analytics-platform/using/cja-connections/overview",
    "https://experienceleague.adobe.com/en/docs/analytics-platform/using/cja-dataviews/data-views",
    "https://experienceleague.adobe.com/en/docs/analytics-platform/using/guided-analysis/overview",
    "https://experienceleague.adobe.com/en/docs/analytics-platform/using/cja-usecases/cross-channel/cross-channel",
    "https://experienceleague.adobe.com/en/docs/analytics-platform/using/compare-aa-cja/cja-aa-comparison/cja-aa",
]
REPORT_CSV = _ROOT / "reports" / "cja_toc_exl_mapping.csv"
OVERRIDES_JSON = _ROOT / "config" / "cja_toc_exl_overrides.json"
CJA_TOC_ROOTS = [
    "help/cja-main/TOC.md",
    "help/cja-main/analysis-workspace/TOC.md",
    "help/cja-main/connections/TOC.md",
    "help/cja-main/data-views/TOC.md",
    "help/cja-main/components/TOC.md",
    "help/cja-main/use-cases/TOC.md",
    "help/cja-main/guided-analysis/TOC.md",
    "help/cja-main/cja-basics/TOC.md",
    "help/cja-main/permissions/TOC.md",
    "help/video-clips/TOC.md",
]
LINK_RE = re.compile(
    r'https://experienceleague\.adobe\.com/en/docs/analytics-platform/using/[a-zA-Z0-9_\-./%]+'
)


@dataclass
class MappingRow:
    toc_file: str
    section: str
    title: str
    repo_path: str
    derived_url: str
    exl_url: str
    match_method: str
    http_status: str


def _gh_headers() -> dict[str, str]:
    token = os.getenv("GITHUB_TOKEN", "")
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def fetch_raw(path: str) -> str | None:
    url = f"{RAW}/{path}"
    try:
        resp = requests.get(url, headers=_gh_headers(), timeout=30)
        if resp.status_code == 200:
            return resp.text
    except Exception:
        pass
    return None


def discover_toc_files() -> list[str]:
    """Return TOC paths that exist in the repo (API if token, else static list)."""
    found: list[str] = []
    token = os.getenv("GITHUB_TOKEN", "")
    if token:
        url = f"https://api.github.com/repos/{GITHUB}/git/trees/{BRANCH}?recursive=1"
        resp = requests.get(url, headers=_gh_headers(), timeout=90)
        if resp.status_code == 200:
            for item in resp.json().get("tree", []):
                p = item.get("path", "")
                if p.endswith("TOC.md") and (
                    "cja-main" in p or p.startswith("help/video-clips/")
                ):
                    found.append(p)
            return sorted(found)

    for path in CJA_TOC_ROOTS:
        if fetch_raw(path):
            found.append(path)
    return found


def parse_all_tocs() -> dict[str, dict]:
    """repo_path → {toc_file, section, title}."""
    merged: dict[str, dict] = {}
    for toc_path in discover_toc_files():
        content = fetch_raw(toc_path)
        if not content:
            continue
        base = str(Path(toc_path).parent)
        for repo_path, info in parse_toc_file(content, base).items():
            merged[repo_path] = {
                "toc_file": toc_path,
                "section": info.get("section", ""),
                "title": info.get("toc_title", ""),
            }
        time.sleep(0.1)
    return merged


def load_repo_paths(csv_path: Path | None) -> list[str]:
    paths: set[str] = set()
    if csv_path and csv_path.exists():
        with open(csv_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("repo") == f"AdobeDocs/{GITHUB.split('/')[1]}" or (
                    "analytics-platform.en" in row.get("repo", "")
                ):
                    paths.add(row["repo_path"])
    return sorted(paths)


def exl_urls_from_redirects() -> set[str]:
    """Collect redirect destination URLs only (canonical targets)."""
    urls: set[str] = set()
    for dst in _load_redirects().values():
        if "/analytics-platform/using/" in dst:
            urls.add(dst.split("?")[0].rstrip("/"))
    return urls


def crawl_exl_urls(seeds: list[str]) -> set[str]:
    found: set[str] = set()
    headers = {"User-Agent": "Mozilla/5.0 (compatible; ExLChatbot/1.0)"}
    with httpx.Client(headers=headers, timeout=20.0, follow_redirects=True) as client:
        for seed in seeds:
            try:
                html = client.get(seed).text
                for match in LINK_RE.findall(html):
                    found.add(match.split("?")[0].rstrip("/"))
            except Exception:
                continue
            time.sleep(0.2)
    return found


def slug_variants(repo_path: str) -> list[str]:
    stem = Path(repo_path).stem
    variants = {stem}
    for suffix in ("-in-customer-journey-analytics", "-in-cja"):
        if stem.endswith(suffix):
            variants.add(stem[: -len(suffix)])
    if stem == "overview":
        variants.add("home")
    return list(variants)


def best_exl_match(repo_path: str, catalog: dict[str, str]) -> str | None:
    """Match repo path to EXL URL catalog by trailing slug segments."""
    variants = slug_variants(repo_path)
    hits: list[str] = []
    for url in catalog:
        tail = url.rsplit("/", 1)[-1]
        if tail in variants:
            hits.append(url)
    if len(hits) == 1:
        return hits[0]
    if not hits:
        return None
    # Prefer paths that share more folder tokens with repo_path
    repo_tokens = set(Path(repo_path).parts)
    hits.sort(
        key=lambda u: sum(1 for p in u.split("/") if p in repo_tokens),
        reverse=True,
    )
    return hits[0]


async def build_rows(repo_paths: list[str], toc_map: dict[str, dict]) -> list[MappingRow]:
    catalog_candidates = exl_urls_from_redirects() | crawl_exl_urls(EXL_SEEDS)
    live_catalog_map = await validate_urls(sorted(catalog_candidates))
    exl_catalog = {
        u.rstrip("/"): u.rstrip("/")
        for u, ok in live_catalog_map.items()
        if ok
    }

    preliminary: list[MappingRow] = []
    for repo_path in repo_paths:
        s3_key = f"{S3_PREFIX}{repo_path}"
        derived = derive_exl_url(s3_key) or ""
        toc = toc_map.get(repo_path, {})
        exl_url = derived
        method = "derived" if derived else "unmapped"

        if derived and derived not in exl_catalog:
            exl_catalog[derived.rstrip("/")] = derived.rstrip("/")

        preliminary.append(
            MappingRow(
                toc_file=toc.get("toc_file", ""),
                section=toc.get("section", ""),
                title=toc.get("title", ""),
                repo_path=repo_path,
                derived_url=derived,
                exl_url=exl_url,
                match_method=method,
                http_status="pending",
            )
        )

    urls_to_check = list(
        dict.fromkeys(r.exl_url for r in preliminary if is_specific_url(r.exl_url))
    )
    live_map = await validate_urls(urls_to_check)

    rows: list[MappingRow] = []
    for row in preliminary:
        if is_specific_url(row.exl_url) and live_map.get(row.exl_url, False):
            row.http_status = "live"
            rows.append(row)
            continue

        matched = best_exl_match(row.repo_path, exl_catalog)
        if matched:
            row.exl_url = matched
            row.match_method = "toc_slug_match"
            row.http_status = "pending"
        else:
            row.http_status = "dead" if row.exl_url else "unmapped"
        rows.append(row)

    # Re-validate slug matches
    recheck = list(
        dict.fromkeys(
            r.exl_url for r in rows if r.http_status == "pending" and is_specific_url(r.exl_url)
        )
    )
    if recheck:
        live2 = await validate_urls(recheck)
        for row in rows:
            if row.http_status == "pending" and is_specific_url(row.exl_url):
                row.http_status = "live" if live2.get(row.exl_url, False) else "dead"

    return rows


def write_outputs(rows: list[MappingRow]) -> None:
    REPORT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "toc_file",
                "section",
                "title",
                "repo_path",
                "derived_url",
                "exl_url",
                "match_method",
                "http_status",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row.toc_file,
                    row.section,
                    row.title,
                    row.repo_path,
                    row.derived_url,
                    row.exl_url,
                    row.match_method,
                    row.http_status,
                ]
            )

    overrides = {
        row.repo_path: row.exl_url
        for row in rows
        if row.http_status == "live"
        and row.exl_url
        and not row.repo_path.startswith("help/video-clips/")
    }

    OVERRIDES_JSON.parent.mkdir(parents=True, exist_ok=True)
    OVERRIDES_JSON.write_text(json.dumps(dict(sorted(overrides.items())), indent=2))

    live = sum(1 for r in rows if r.http_status == "live")
    dead = sum(1 for r in rows if r.http_status == "dead")
    unmapped = sum(1 for r in rows if r.http_status == "unmapped")
    print(f"Wrote {REPORT_CSV} ({len(rows)} rows)")
    print(f"Wrote {OVERRIDES_JSON} ({len(overrides)} overrides)")
    print(f"Summary: live={live} dead={dead} unmapped={unmapped}")


async def run(paths_csv: Path | None) -> int:
    toc_map = parse_all_tocs()
    print(f"TOC entries parsed: {len(toc_map)}")

    repo_paths = load_repo_paths(paths_csv)
    if toc_map:
        for p in toc_map:
            if p not in repo_paths:
                repo_paths.append(p)
        repo_paths.sort()

    if not repo_paths:
        print("No repo paths to map.", file=sys.stderr)
        return 1

    rows = await build_rows(repo_paths, toc_map)
    write_outputs(rows)
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--paths-csv",
        type=Path,
        default=_ROOT / "reports" / "exl_validation.csv",
        help="Seed repo paths (default: reports/exl_validation.csv)",
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(args.paths_csv)))


if __name__ == "__main__":
    main()
