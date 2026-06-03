#!/usr/bin/env python3
"""
Build metadata registry entries for Adobe Target docs.

Scans adobe-docs/adobe-target/ in S3, constructs EL URLs using Target's
path transformation rules, and merges into data/metadata_registry.json.

URL pattern:
  S3:  adobe-docs/adobe-target/help/main/c-activities/t-test-ab/test-ab.md
  EL:  https://experienceleague.adobe.com/en/docs/target/using/activities/test-ab/test-ab

Rules:
  1. Strip adobe-docs/adobe-target/help/main/ prefix
  2. Strip c- / t- / r- prefixes from each directory component
  3. Strip .md extension from filename
  4. Prepend https://experienceleague.adobe.com/en/docs/target/using/
"""

import json
import logging
import re
import sys
from pathlib import Path

import boto3
from dotenv import load_dotenv

_ROOT = Path(__file__).parent.parent
load_dotenv(_ROOT / ".env")
sys.path.insert(0, str(_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s")
logger = logging.getLogger(__name__)

REGISTRY_PATH = _ROOT / "data" / "metadata_registry.json"
S3_BUCKET = "experienceleaguechatbot"
S3_PREFIX = "adobe-docs/adobe-target/help/main/"
EL_BASE = "https://experienceleague.adobe.com/en/docs/target/using"

_DIR_PREFIX_RE = re.compile(r"^[ctrkr]-")  # strip c-, t-, r-, k- prefixes
_SKIP_FILES = {"TOC.md", "overview.md"}


def s3_key_to_el_url(s3_key: str) -> str:
    """Convert an S3 key to an Experience League URL."""
    # Strip S3 prefix
    rel = s3_key.removeprefix(S3_PREFIX)

    # Skip index/TOC files
    filename = rel.split("/")[-1]
    if filename in _SKIP_FILES:
        return ""

    # Split into parts, strip prefixes, strip .md
    parts = rel.replace(".md", "").split("/")
    clean_parts = [_DIR_PREFIX_RE.sub("", p) for p in parts]

    return f"{EL_BASE}/{'/'.join(clean_parts)}"


def extract_frontmatter(content: str) -> dict:
    """Extract YAML frontmatter fields."""
    meta = {}
    if not content.startswith("---"):
        return meta
    end = content.find("\n---", 3)
    if end == -1:
        return meta
    fm = content[3:end]
    for line in fm.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            meta[key.strip().lower()] = val.strip().strip('"').strip("'")
    return meta


def main():
    import os

    s3 = boto3.client("s3", region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"))

    # Load existing registry
    registry = {}
    if REGISTRY_PATH.exists():
        registry = json.loads(REGISTRY_PATH.read_text())
    before = len(registry)

    # List all Target .md files in S3
    paginator = s3.get_paginator("list_objects_v2")
    md_keys = []
    for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=S3_PREFIX):
        for obj in page.get("Contents", []):
            if obj["Key"].endswith(".md"):
                md_keys.append(obj["Key"])

    logger.info(f"Found {len(md_keys)} Target markdown files in S3")

    added = 0
    skipped = 0

    for key in md_keys:
        el_url = s3_key_to_el_url(key)
        if not el_url:
            skipped += 1
            continue

        # Download and parse frontmatter
        try:
            resp = s3.get_object(Bucket=S3_BUCKET, Key=key)
            content = resp["Body"].read().decode("utf-8", errors="replace")
            fm = extract_frontmatter(content)
        except Exception as e:
            logger.warning(f"Could not read {key}: {e}")
            fm = {}

        title = fm.get("title") or Path(key).stem.replace("-", " ").title()
        description = fm.get("description", "")
        if len(description) > 200:
            description = description[:200] + "..."

        registry[key] = {
            "title": title,
            "experience_league_url": el_url,
            "github_url": f"https://github.com/AdobeDocs/target.en/blob/main/{key.removeprefix('adobe-docs/adobe-target/')}",
            "product": "Adobe Target",
            "doc_type": fm.get("feature", "Article"),
            "role": "User",
            "level": "Beginner",
            "description": description,
        }
        added += 1

    # Save updated registry
    REGISTRY_PATH.write_text(json.dumps(registry, indent=2))
    logger.info(f"Registry updated: {before} → {len(registry)} entries (+{added} Target, {skipped} skipped)")


if __name__ == "__main__":
    main()
