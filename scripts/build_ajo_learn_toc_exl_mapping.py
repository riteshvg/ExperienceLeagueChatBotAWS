#!/usr/bin/env python3
"""
Build journey-optimizer-learn.en repo_path -> Experience League URL mapping.

Unlike analytics-learn.en (a flat folder-to-URL mapping), most sections of this
repo are renamed on publish (e.g. help/tutorial-identity-stitching/ publishes
under .../tutorial-on-identity-stitching-in-aep/). The rename is not derivable
from the GitHub folder name alone, but every section's own TOC.md front matter
carries a `breadcrumb-url:` field pointing at that section's live landing page
-- which tells us exactly what the folder was renamed to. This script:

1. Discovers every top-level help/<section>/TOC.md (case-insensitive, since at
   least one repo has a lowercase toc.md)
2. Parses each TOC's `breadcrumb-url` + its list of member files
3. Derives the folder rename by diffing breadcrumb-url against the landing
   (first-listed) entry's own repo-relative path
4. Applies that rename to every other file in the section (same depth, filenames
   unchanged) and HTTP-validates the result
5. Writes reports/ajo_learn_toc_exl_mapping.csv (audit trail) and
   config/ajo_learn_toc_exl_overrides.json (validated live URLs only)

`help/_ajo-main/` is deliberately excluded: it has no `breadcrumb-url` in its
own TOC.md, and spot checks showed its sub-paths are renamed per TOC *section
heading* (not a single folder rename), which this script's model doesn't
capture. Leave it unmapped rather than guess -- see dbupload.md's tracker.

Usage:
    python3 scripts/build_ajo_learn_toc_exl_mapping.py
"""

from __future__ import annotations

import asyncio
import csv
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import requests
from dotenv import load_dotenv

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))
load_dotenv(_ROOT / ".env")

from scripts.extract_metadata_from_github import parse_toc_file  # noqa: E402
from src.utils.citation_metadata import validate_urls  # noqa: E402

BRANCH = "main"
GITHUB = "AdobeDocs/journey-optimizer-learn.en"
BASE_URL = "https://experienceleague.adobe.com/en/docs/journey-optimizer-learn"

# Sections known not to need/have a rename mapping worth pursuing here.
EXCLUDED_TOP_FOLDERS = ("_ajo-main", "video-clips", "video-shorts")

# A few sections rename a *nested* subfolder too, not just the top-level one --
# confirmed by checking a live sibling page's own outbound links (e.g.
# mobile-learning-hub/overview links to .../mobile-channels-overview/*, not
# .../channels/*). {top_folder: {old_subfolder: new_subfolder}}
SUBFOLDER_RENAMES: dict[str, dict[str, str]] = {
    "mobile-learning-hub": {"channels": "mobile-channels-overview"},
}

REPORT_CSV = _ROOT / "reports" / "ajo_learn_toc_exl_mapping.csv"
OVERRIDES_JSON = _ROOT / "config" / "ajo_learn_toc_exl_overrides.json"

BREADCRUMB_RE = re.compile(r"breadcrumb-url:\s*(\S+)")


@dataclass
class MappingRow:
    toc_file: str
    top_folder: str
    new_top: str
    repo_path: str
    exl_url: str
    http_status: str


def _gh_headers() -> dict[str, str]:
    token = os.getenv("GITHUB_TOKEN", "")
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def fetch_raw(path: str) -> str | None:
    url = f"https://raw.githubusercontent.com/{GITHUB}/{BRANCH}/{path}"
    try:
        resp = requests.get(url, headers=_gh_headers(), timeout=30)
        if resp.status_code == 200:
            return resp.text
    except Exception:
        pass
    return None


def discover_toc_files() -> list[str]:
    """Every top-level help/<section>/TOC.md (any case), one section per file."""
    url = f"https://api.github.com/repos/{GITHUB}/git/trees/{BRANCH}?recursive=1"
    resp = requests.get(url, headers=_gh_headers(), timeout=90)
    resp.raise_for_status()
    found = []
    for item in resp.json().get("tree", []):
        p = item.get("path", "")
        parts = p.split("/")
        if len(parts) == 3 and parts[0] == "help" and parts[2].lower() == "toc.md":
            found.append(p)
    return sorted(found)


def strip_ext(path: str) -> str:
    for ext in (".html", ".md"):
        if path.endswith(ext):
            return path[: -len(ext)]
    return path


def derive_section_mapping(toc_path: str) -> tuple[str, str, dict[str, dict]] | None:
    """
    Returns (top_folder, new_top, {repo_path: {toc_title}}) for one section,
    or None if the section has no usable breadcrumb-url or can't be diffed.
    """
    top_folder = toc_path.split("/")[1]
    if top_folder in EXCLUDED_TOP_FOLDERS:
        return None

    content = fetch_raw(toc_path)
    if not content:
        return None

    m = BREADCRUMB_RE.search(content)
    if not m:
        return None
    breadcrumb = m.group(1).strip()
    breadcrumb = breadcrumb.split("/docs/journey-optimizer-learn/", 1)[-1]
    breadcrumb = strip_ext(breadcrumb).strip("/")

    base = str(Path(toc_path).parent)  # e.g. "help/challenges"
    raw_entries = parse_toc_file(content, base)
    if not raw_entries:
        return None
    # TOC entries use repo-root-absolute links ("/help/x/y.md"), which
    # os.path.join treats as absolute and returns unchanged -- strip the
    # leading slash. Relative links ("./y.md") leave a literal "./" segment
    # that os.path.join doesn't collapse -- normalize that away too.
    entries = {
        os.path.normpath(path.lstrip("/")): info for path, info in raw_entries.items()
    }

    # First-listed entry is the section's own landing page (convention observed
    # across all 16 sections checked) -- use it to diff out the folder rename.
    first_repo_path = next(iter(entries))  # e.g. "help/challenges/introduction-and-prerequisites.md"
    landing_relative = strip_ext(first_repo_path[len(f"help/{top_folder}/"):])
    depth = landing_relative.count("/") + 1

    breadcrumb_parts = breadcrumb.split("/")
    if len(breadcrumb_parts) < depth:
        return None
    new_top = "/".join(breadcrumb_parts[:-depth]) if depth < len(breadcrumb_parts) else ""
    if not new_top:
        # depth consumed the whole breadcrumb -- rename target has no fixed
        # prefix distinct from the varying tail; not safely generalizable.
        return None

    return top_folder, new_top, entries


async def build_rows() -> list[MappingRow]:
    rows: list[MappingRow] = []
    for toc_path in discover_toc_files():
        result = derive_section_mapping(toc_path)
        if not result:
            print(f"  skip (no usable breadcrumb-url): {toc_path}")
            continue
        top_folder, new_top, entries = result
        print(f"  {top_folder} -> {new_top}  ({len(entries)} files)")

        old_prefix = f"help/{top_folder}/"
        subfolder_renames = SUBFOLDER_RENAMES.get(top_folder, {})
        for repo_path in entries:
            if not repo_path.startswith(old_prefix):
                continue
            tail = strip_ext(repo_path[len(old_prefix):])
            tail_parts = tail.split("/")
            if len(tail_parts) > 1 and tail_parts[0] in subfolder_renames:
                tail_parts[0] = subfolder_renames[tail_parts[0]]
                tail = "/".join(tail_parts)
            exl_url = f"{BASE_URL}/{new_top}/{tail}"
            rows.append(
                MappingRow(
                    toc_file=toc_path,
                    top_folder=top_folder,
                    new_top=new_top,
                    repo_path=repo_path,
                    exl_url=exl_url,
                    http_status="pending",
                )
            )
        time.sleep(0.1)

    urls = list(dict.fromkeys(r.exl_url for r in rows))
    live_map = await validate_urls(urls)
    for row in rows:
        row.http_status = "live" if live_map.get(row.exl_url, False) else "dead"
    return rows


def write_outputs(rows: list[MappingRow]) -> None:
    REPORT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["toc_file", "top_folder", "new_top", "repo_path", "exl_url", "http_status"])
        for row in rows:
            writer.writerow(
                [row.toc_file, row.top_folder, row.new_top, row.repo_path, row.exl_url, row.http_status]
            )

    overrides = {row.repo_path: row.exl_url for row in rows if row.http_status == "live"}
    OVERRIDES_JSON.parent.mkdir(parents=True, exist_ok=True)
    OVERRIDES_JSON.write_text(json.dumps(dict(sorted(overrides.items())), indent=2))

    live = sum(1 for r in rows if r.http_status == "live")
    dead = sum(1 for r in rows if r.http_status == "dead")
    print(f"\nWrote {REPORT_CSV} ({len(rows)} rows)")
    print(f"Wrote {OVERRIDES_JSON} ({len(overrides)} overrides)")
    print(f"Summary: live={live} dead={dead}")


async def run() -> int:
    rows = await build_rows()
    if not rows:
        print("No rows built.", file=sys.stderr)
        return 1
    write_outputs(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
