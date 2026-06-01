#!/usr/bin/env python3
"""
Enrich ChromaDB chunks with media metadata extracted from the markdown content already in the DB.

Extracts from frontmatter and body:
  - thumbnail URL  (thumbnail: <id>.jpg → https://video.tv.adobe.com/v/<id>)
  - video URL      (>[!VIDEO](<url>) tags)
  - image URLs     (![alt](https://...)) in body

Writes thumbnail_url, video_url, image_urls back to each chunk's metadata.

Usage:
    python scripts/ingest_with_media.py
    python scripts/ingest_with_media.py --dry-run
    python scripts/ingest_with_media.py --product "Customer Journey Analytics"
"""

import argparse
import json
import logging
import re
import sys
from collections import defaultdict
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s")
logger = logging.getLogger(__name__)

CHROMA_DIR = _ROOT / "chroma_db"
COLLECTION_NAME = "experience_league"

ADOBE_THUMB_CDN = "https://cdn.experienceleague.adobe.com/thumb"

# S3 key prefix → GitHub raw CDN base URL
GITHUB_RAW_BASES = {
    "adobe-docs/adobe-analytics/": "https://raw.githubusercontent.com/AdobeDocs/analytics.en/main/",
    "adobe-docs/customer-journey-analytics/": "https://raw.githubusercontent.com/AdobeDocs/analytics-platform.en/main/",
    "adobe-docs/experience-platform/": "https://raw.githubusercontent.com/AdobeDocs/experience-platform.en/main/",
}

# Regex patterns
RE_THUMBNAIL = re.compile(r"^thumbnail:\s*(\S+)", re.MULTILINE)
RE_VIDEO_TAG = re.compile(r">\[!VIDEO\]\(([^)]+)\)")
RE_IMG_ALL = re.compile(r"!\[([^\]]*)\]\(([^)]+\.(?:png|jpg|jpeg|gif|webp))[^)]*\)", re.IGNORECASE)


def resolve_image_url(img_path: str, s3_key: str) -> str | None:
    """Resolve a relative markdown image path to an absolute GitHub CDN URL."""
    if img_path.startswith("http"):
        return img_path  # already absolute

    # Find the GitHub base for this s3_key
    github_base = None
    for prefix, base in GITHUB_RAW_BASES.items():
        if s3_key.startswith(prefix):
            # Strip the s3 prefix to get the repo-relative path
            repo_path = s3_key[len(prefix):]
            github_base = base + repo_path
            break

    if not github_base:
        return None

    # github_base is now the full path to the .md file, get its directory
    doc_dir = github_base.rsplit("/", 1)[0] + "/"

    if img_path.startswith("/"):
        # Absolute repo path — resolve against GitHub base root
        for prefix, base in GITHUB_RAW_BASES.items():
            if s3_key.startswith(prefix):
                return base + img_path.lstrip("/")
    elif img_path.startswith("./"):
        return doc_dir + img_path[2:]
    else:
        return doc_dir + img_path

    return None


def extract_media_from_markdown(content: str, page_url: str, s3_key: str = "") -> dict:
    """Parse markdown frontmatter and body for thumbnail, video, and image URLs."""
    media = {"thumbnail_url": None, "video_url": None, "image_urls": []}

    # 1. >[!VIDEO](...) tag — most reliable
    video_match = RE_VIDEO_TAG.search(content)
    if video_match:
        media["video_url"] = video_match.group(1).strip()

    # 2. thumbnail: frontmatter field — e.g. "334261.jpg" or "3421621.jpeg"
    thumb_match = RE_THUMBNAIL.search(content)
    if thumb_match:
        thumb_id = thumb_match.group(1).strip()
        media["thumbnail_url"] = f"{ADOBE_THUMB_CDN}/{thumb_id}"

    # 3. Image references — resolve relative paths to GitHub CDN absolute URLs
    for m in RE_IMG_ALL.finditer(content):
        alt = m.group(1).lower()
        img_path = m.group(2)
        # Skip icons and tiny decorative images
        if any(x in alt for x in ["icon", "logo", "badge", "check", "smock"]):
            continue
        if any(x in img_path.lower() for x in ["icon", "logo", "smock", ".svg"]):
            continue
        resolved = resolve_image_url(img_path, s3_key)
        if resolved and resolved not in media["image_urls"]:
            media["image_urls"].append(resolved)
        if len(media["image_urls"]) >= 4:
            break

    return media


def process_collection(collection, product_filter: str = "", dry_run: bool = False) -> dict:
    """
    Group chunks by URL, extract media from chunk_index=0 (contains frontmatter),
    then update all chunks for that URL.
    """
    # Fetch all chunks
    logger.info("Fetching all chunks from ChromaDB…")
    results = collection.get(include=["documents", "metadatas"])
    ids = results["ids"]
    docs = results["documents"]
    metas = results["metadatas"]
    logger.info(f"Total chunks: {len(ids)}")

    # Group by URL, keeping the first chunk's content (has frontmatter)
    url_to_first_chunk: dict[str, dict] = {}
    url_to_all_ids: dict[str, list] = defaultdict(list)
    url_to_all_metas: dict[str, list] = defaultdict(list)

    for cid, doc, meta in zip(ids, docs, metas):
        url = meta.get("url", "")
        if not url or url == "https://experienceleague.adobe.com/en/docs":
            continue
        if product_filter and product_filter.lower() not in meta.get("product", "").lower():
            continue

        url_to_all_ids[url].append(cid)
        url_to_all_metas[url].append(meta)

        if meta.get("chunk_index", 999) == 0:
            url_to_first_chunk[url] = {"doc": doc, "meta": meta}

    logger.info(f"Unique URLs to process: {len(url_to_first_chunk)}")

    stats = {"pages": 0, "chunks": 0, "with_video": 0, "with_thumbnail": 0, "with_images": 0}
    results_log = []

    for url, first in url_to_first_chunk.items():
        s3_key = first["meta"].get("s3_key", "")
        media = extract_media_from_markdown(first["doc"], url, s3_key=s3_key)

        has_media = media["video_url"] or media["thumbnail_url"] or media["image_urls"]
        if not has_media:
            continue

        chunk_ids = url_to_all_ids[url]
        all_metas = url_to_all_metas[url]

        updated_metas = []
        for meta in all_metas:
            new_meta = dict(meta)
            if media["thumbnail_url"]:
                new_meta["thumbnail_url"] = media["thumbnail_url"]
            if media["video_url"]:
                new_meta["video_url"] = media["video_url"]
            if media["image_urls"]:
                new_meta["image_urls"] = json.dumps(media["image_urls"])
            updated_metas.append(new_meta)

        if not dry_run:
            collection.update(ids=chunk_ids, metadatas=updated_metas)

        stats["pages"] += 1
        stats["chunks"] += len(chunk_ids)
        if media["video_url"]:
            stats["with_video"] += 1
        if media["thumbnail_url"]:
            stats["with_thumbnail"] += 1
        if media["image_urls"]:
            stats["with_images"] += 1

        results_log.append({
            "url": url,
            "title": first["meta"].get("title", ""),
            "product": first["meta"].get("product", ""),
            "chunks": len(chunk_ids),
            "thumbnail_url": media["thumbnail_url"],
            "video_url": media["video_url"],
            "image_count": len(media["image_urls"]),
        })

        logger.debug(
            f"  {first['meta'].get('title','')[:50]} | "
            f"video={'✓' if media['video_url'] else '✗'} | "
            f"thumb={'✓' if media['thumbnail_url'] else '✗'} | "
            f"imgs={len(media['image_urls'])}"
        )

    return stats, results_log


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--product", default="", help="Filter by product name")
    args = parser.parse_args()

    chroma = chromadb.PersistentClient(
        path=str(CHROMA_DIR),
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    col = chroma.get_collection(COLLECTION_NAME)

    stats, results_log = process_collection(col, product_filter=args.product, dry_run=args.dry_run)

    action = "Would update" if args.dry_run else "Updated"
    logger.info(f"\n{'='*60}")
    logger.info(f"Pages with media    : {stats['pages']}")
    logger.info(f"Chunks {action:<10}: {stats['chunks']}")
    logger.info(f"  → with video      : {stats['with_video']}")
    logger.info(f"  → with thumbnail  : {stats['with_thumbnail']}")
    logger.info(f"  → with images     : {stats['with_images']}")

    out_path = _ROOT / "data" / "media_ingest_results.json"
    with open(out_path, "w") as f:
        json.dump(results_log, f, indent=2)
    logger.info(f"Results saved to {out_path}")

    # Print first 10 enriched pages as sample
    sample = [r for r in results_log if r["video_url"]][:10]
    if sample:
        logger.info("\nSample enriched pages (with video):")
        for r in sample:
            logger.info(f"  [{r['product'][:3]}] {r['title'][:55]:<55} video={r['video_url'][:50]}")


if __name__ == "__main__":
    main()
