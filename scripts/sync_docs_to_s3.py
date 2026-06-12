#!/usr/bin/env python3
"""
Delta sync: AdobeDocs GitHub repos → S3

Only downloads files whose SHA has changed since last sync.
Stores a manifest at data/sync_manifest.json to track state.

Usage:
    python scripts/sync_docs_to_s3.py [--dry-run] [--force]
    python scripts/sync_docs_to_s3.py --repo analytics.en  # single repo

Requires: GITHUB_TOKEN env var (optional but raises rate limit from 60→5000 req/hr)
"""

import argparse
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import boto3
import requests
from dotenv import load_dotenv

_ROOT = Path(__file__).parent.parent
load_dotenv(_ROOT / ".env")
sys.path.insert(0, str(_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s")
logger = logging.getLogger(__name__)

MANIFEST_PATH = _ROOT / "data" / "sync_manifest.json"
REGISTRY_PATH = _ROOT / "data" / "metadata_registry.json"
CHANGED_KEYS_PATH = _ROOT / "data" / "changed_s3_keys.txt"
S3_BUCKET = os.getenv("AWS_S3_BUCKET", "experienceleaguechatbot")

REPOS = {
    "adobe-docs/adobe-analytics": {
        "github": "AdobeDocs/analytics.en",
        "branch": "main",
        "s3_prefix": "adobe-docs/adobe-analytics/",
        "path_filter": "help/",        # only ingest help/ subdirectory
    },
    "adobe-docs/customer-journey-analytics": {
        "github": "AdobeDocs/analytics-platform.en",
        "branch": "main",
        "s3_prefix": "adobe-docs/customer-journey-analytics/",
        "path_filter": "help/",
    },
    "adobe-docs/experience-platform": {
        "github": "AdobeDocs/experience-platform.en",
        "branch": "main",
        "s3_prefix": "adobe-docs/experience-platform/",
        "path_filter": "help/",
        "experience_league_base": "https://experienceleague.adobe.com/en/docs/experience-platform",
        "url_path_strip": "help/",
        "product": "Adobe Experience Platform",
        "doc_type": "guide",
        "level": "intermediate",
    },
    "adobe-docs/adobe-target": {
        "github": "AdobeDocs/target.en",
        "branch": "main",
        "s3_prefix": "adobe-docs/adobe-target/",
        "path_filter": "help/main/",   # skip help/flags/ and tutorials/
    },
    # ── Adobe Data Collection ──────────────────────────────────────────────────
    # Tags/Launch (help/tags/ lives inside experience-platform.en)
    "adobe-docs/data-collection-tags": {
        "github": "AdobeDocs/experience-platform.en",
        "branch": "main",
        "s3_prefix": "adobe-docs/data-collection/",
        "path_filter": "help/tags/",
        "experience_league_base": "https://experienceleague.adobe.com/en/docs/experience-platform",
        "url_path_strip": "help/",
        "product": "Adobe Data Collection",
        "doc_type": "guide",
        "level": "intermediate",
    },
    # Web SDK
    "adobe-docs/data-collection-web-sdk": {
        "github": "AdobeDocs/experience-platform.en",
        "branch": "main",
        "s3_prefix": "adobe-docs/data-collection/",
        "path_filter": "help/web-sdk/",
        "experience_league_base": "https://experienceleague.adobe.com/en/docs/experience-platform",
        "url_path_strip": "help/",
        "product": "Adobe Data Collection",
        "doc_type": "guide",
        "level": "intermediate",
    },
    # Datastreams
    "adobe-docs/data-collection-datastreams": {
        "github": "AdobeDocs/experience-platform.en",
        "branch": "main",
        "s3_prefix": "adobe-docs/data-collection/",
        "path_filter": "help/datastreams/",
        "experience_league_base": "https://experienceleague.adobe.com/en/docs/experience-platform",
        "url_path_strip": "help/",
        "product": "Adobe Data Collection",
        "doc_type": "guide",
        "level": "intermediate",
    },
    # Edge Network / Collection
    "adobe-docs/data-collection-collection": {
        "github": "AdobeDocs/experience-platform.en",
        "branch": "main",
        "s3_prefix": "adobe-docs/data-collection/",
        "path_filter": "help/collection/",
        "experience_league_base": "https://experienceleague.adobe.com/en/docs/experience-platform",
        "url_path_strip": "help/",
        "product": "Adobe Data Collection",
        "doc_type": "guide",
        "level": "intermediate",
    },
    # Platform Learn tutorials (entire repo)
    "adobe-docs/platform-learn": {
        "github": "AdobeDocs/platform-learn.en",
        "branch": "main",
        "s3_prefix": "adobe-docs/platform-learn/",
        "path_filter": "",
        "experience_league_base": "https://experienceleague.adobe.com/en/docs/platform-learn",
        "url_path_strip": "",
        "product": "Adobe Data Collection",
        "doc_type": "tutorial",
        "level": "beginner",
    },
    # ── Adobe Journey Optimizer ────────────────────────────────────────────────
    "adobe-docs/adobe-journey-optimizer": {
        "github": "AdobeDocs/journey-optimizer.en",
        "branch": "main",
        "s3_prefix": "adobe-docs/adobe-journey-optimizer/",
        "path_filter": "help/",
        "experience_league_base": "https://experienceleague.adobe.com/en/docs/journey-optimizer",
        "url_path_strip": "help/",
        "product": "Adobe Journey Optimizer",
        "doc_type": "guide",
        "level": "intermediate",
    },
}


def _load_registry() -> dict:
    if REGISTRY_PATH.exists():
        return json.loads(REGISTRY_PATH.read_text())
    return {}


def _save_registry(registry: dict) -> None:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(json.dumps(registry, indent=2, sort_keys=True))


def _extract_title(content: bytes, path: str) -> str:
    """Extract title from markdown frontmatter or first H1, fallback to filename."""
    try:
        text = content.decode("utf-8", errors="ignore")
        fm = re.search(r'^---\s*\n(.*?)\n---', text, re.DOTALL)
        if fm:
            m = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', fm.group(1), re.MULTILINE)
            if m:
                return m.group(1).strip()
        h1 = re.search(r'^#\s+(.+)$', text, re.MULTILINE)
        if h1:
            return h1.group(1).strip()
    except Exception:
        pass
    return Path(path).stem.replace("-", " ").replace("_", " ").title()


def _generate_registry_entry(s3_key: str, path: str, content: bytes, config: dict) -> dict:
    """Generate a metadata_registry.json entry for a new-source file."""
    el_base = config["experience_league_base"].rstrip("/")
    url_strip = config.get("url_path_strip", "help/")
    url_path = path[:-3] if path.endswith(".md") else path
    if url_strip and url_path.startswith(url_strip):
        url_path = url_path[len(url_strip):]
    return {
        "s3_key": s3_key,
        "url": f"{el_base}/{url_path}",
        "title": _extract_title(content, path),
        "product": config["product"],
        "doc_type": config.get("doc_type", "guide"),
        "level": config.get("level", "intermediate"),
    }


def _gh_headers() -> dict:
    token = os.getenv("GITHUB_TOKEN", "")
    h = {"Accept": "application/vnd.github.v3+json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text())
    return {}


def _save_manifest(manifest: dict) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))


def get_repo_tree(repo: str, branch: str) -> List[dict]:
    """Fetch full recursive file tree for a repo."""
    url = f"https://api.github.com/repos/{repo}/git/trees/{branch}?recursive=1"
    resp = requests.get(url, headers=_gh_headers(), timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if data.get("truncated"):
        logger.warning(f"Tree truncated for {repo} — some files may be missed")
    return [f for f in data.get("tree", []) if f["type"] == "blob"]


def download_file(repo: str, path: str, branch: str) -> bytes:
    """Download raw file content from GitHub."""
    url = f"https://raw.githubusercontent.com/{repo}/{branch}/{path}"
    resp = requests.get(url, headers=_gh_headers(), timeout=30)
    resp.raise_for_status()
    return resp.content


def sync_repo(repo_key: str, config: dict, s3, manifest: dict,
              dry_run: bool = False, force: bool = False,
              registry: Optional[dict] = None) -> dict:
    """Sync one repo. Returns stats dict with 'changed_keys' list."""
    github_repo = config["github"]
    branch = config["branch"]
    s3_prefix = config["s3_prefix"]
    path_filter = config.get("path_filter", "")
    generates_registry = registry is not None and "experience_league_base" in config

    logger.info(f"Fetching tree for {github_repo}...")
    tree = get_repo_tree(github_repo, branch)

    # Filter to markdown files matching the path prefix
    md_files = [
        f for f in tree
        if f["path"].endswith(".md") and f["path"].startswith(path_filter)
    ]
    logger.info(f"  {len(md_files)} markdown files found")

    repo_manifest = manifest.get(repo_key, {})
    stats = {"checked": len(md_files), "updated": 0, "skipped": 0, "errors": 0, "changed_keys": []}

    for i, file in enumerate(md_files):
        path = file["path"]
        sha = file["sha"]
        s3_key = s3_prefix + path

        # Skip if SHA unchanged
        if not force and repo_manifest.get(path) == sha:
            stats["skipped"] += 1
            continue

        if dry_run:
            logger.debug(f"  [dry-run] would update: {path}")
            stats["updated"] += 1
            stats["changed_keys"].append(s3_key)
            continue

        try:
            content = download_file(github_repo, path, branch)
            s3.put_object(Bucket=S3_BUCKET, Key=s3_key, Body=content)
            repo_manifest[path] = sha
            stats["updated"] += 1
            stats["changed_keys"].append(s3_key)
            if generates_registry:
                registry[s3_key] = _generate_registry_entry(s3_key, path, content, config)
            if stats["updated"] % 50 == 0:
                logger.info(f"  Updated {stats['updated']} files so far...")
            # Gentle rate limiting
            time.sleep(0.05)
        except Exception as e:
            logger.warning(f"  Failed {path}: {e}")
            stats["errors"] += 1

    # Ensure every tree file has a registry entry (handles skipped/unchanged files)
    if generates_registry and not dry_run:
        for file in md_files:
            s3_key = s3_prefix + file["path"]
            if s3_key not in registry:
                registry[s3_key] = _generate_registry_entry(
                    s3_key, file["path"], b"", config
                )

    manifest[repo_key] = repo_manifest
    return stats


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="Re-sync all files ignoring manifest")
    parser.add_argument("--repo", help="Sync only this repo key (e.g. adobe-docs/adobe-analytics)")
    args = parser.parse_args()

    s3 = boto3.client("s3", region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
    manifest = _load_manifest()
    registry = _load_registry()

    repos_to_sync = {args.repo: REPOS[args.repo]} if args.repo and args.repo in REPOS else REPOS

    total_updated = 0
    all_changed_keys: list[str] = []

    for repo_key, config in repos_to_sync.items():
        logger.info(f"\n{'='*50}")
        logger.info(f"Syncing {repo_key}")
        stats = sync_repo(repo_key, config, s3, manifest,
                          dry_run=args.dry_run, force=args.force,
                          registry=registry)
        logger.info(f"  checked={stats['checked']} updated={stats['updated']} "
                    f"skipped={stats['skipped']} errors={stats['errors']}")
        total_updated += stats["updated"]
        all_changed_keys.extend(stats["changed_keys"])

    if not args.dry_run:
        manifest["_last_sync"] = datetime.now(timezone.utc).isoformat()
        manifest["_last_updated_count"] = total_updated
        _save_manifest(manifest)
        _save_registry(registry)
        logger.info(f"Registry saved — {len(registry)} total entries")

        # Write changed keys for incremental ingest
        CHANGED_KEYS_PATH.parent.mkdir(parents=True, exist_ok=True)
        CHANGED_KEYS_PATH.write_text("\n".join(all_changed_keys) + ("\n" if all_changed_keys else ""))
        logger.info(f"Changed keys written to {CHANGED_KEYS_PATH} ({len(all_changed_keys)} files)")

    logger.info(f"\nSync complete — {total_updated} files updated")
    return total_updated


if __name__ == "__main__":
    main()
