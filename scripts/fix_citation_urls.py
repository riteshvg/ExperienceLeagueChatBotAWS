"""
One-time cleanup: test all citation URLs in ChromaDB from local machine
and blank out the `url` field for any that return HTTP 404/410.

Run from repo root:
  venv/bin/python3.12 scripts/fix_citation_urls.py

After this runs, re-upload ChromaDB and redeploy Railway:
  venv/bin/python3.12 scripts/upload_chroma_to_s3.py
  railway up
"""

import asyncio
import logging
import ssl
import sys
from pathlib import Path

import chromadb
import httpx
from chromadb.config import Settings as ChromaSettings

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_ROOT = Path(__file__).parent.parent
_CHROMA_PATH = _ROOT / "chroma_db"
_TIMEOUT = 5.0
_CONCURRENCY = 20


async def validate_urls(urls: list[str]) -> dict[str, bool]:
    """Return {url: is_valid} for all given URLs. Tests from local machine."""
    sem = asyncio.Semaphore(_CONCURRENCY)
    results: dict[str, bool] = {}

    async def _check(client: httpx.AsyncClient, url: str) -> None:
        async with sem:
            try:
                r = await client.head(url, follow_redirects=True)
                results[url] = r.status_code not in (404, 410)
            except Exception:
                results[url] = True  # network error → keep

    async with httpx.AsyncClient(
        timeout=_TIMEOUT,
        verify=False,
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
    ) as client:
        await asyncio.gather(*[_check(client, u) for u in urls])

    return results


def main() -> None:
    client = chromadb.PersistentClient(
        path=str(_CHROMA_PATH),
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    col = client.get_collection("experience_league")

    # Fetch all docs
    logger.info("Loading all documents from ChromaDB...")
    all_data = col.get(include=["metadatas"])
    ids = all_data["ids"]
    metas = all_data["metadatas"]
    logger.info(f"Loaded {len(ids)} documents")

    # Collect unique URLs
    url_to_ids: dict[str, list[str]] = {}
    for doc_id, meta in zip(ids, metas):
        url = (meta or {}).get("url", "")
        if url and url.startswith("https://experienceleague.adobe.com"):
            url_to_ids.setdefault(url, []).append(doc_id)

    unique_urls = list(url_to_ids.keys())
    logger.info(f"Found {len(unique_urls)} unique citation URLs to validate")

    # Validate all URLs
    logger.info("Validating URLs (this may take 1-2 minutes)...")
    validity = asyncio.run(validate_urls(unique_urls))

    valid = sum(1 for v in validity.values() if v)
    invalid = sum(1 for v in validity.values() if not v)
    logger.info(f"Valid: {valid}, Dead (404/410): {invalid}")

    # Print dead URLs
    dead_urls = [u for u, ok in validity.items() if not ok]
    logger.info(f"\nDead URLs ({len(dead_urls)}):")
    for u in sorted(dead_urls):
        logger.info(f"  ✗ {u}")

    if not dead_urls:
        logger.info("No dead URLs found — nothing to fix!")
        return

    # Blank out `url` for docs with dead URLs
    ids_to_fix: list[str] = []
    metas_to_fix: list[dict] = []
    for url in dead_urls:
        for doc_id in url_to_ids[url]:
            idx = ids.index(doc_id)
            updated_meta = dict(metas[idx])
            updated_meta["url"] = ""
            ids_to_fix.append(doc_id)
            metas_to_fix.append(updated_meta)

    logger.info(f"\nClearing URL field for {len(ids_to_fix)} document chunks...")
    # Update in batches of 500
    batch = 500
    for start in range(0, len(ids_to_fix), batch):
        col.update(
            ids=ids_to_fix[start:start + batch],
            metadatas=metas_to_fix[start:start + batch],
        )
        logger.info(f"  Updated {min(start + batch, len(ids_to_fix))}/{len(ids_to_fix)}")

    logger.info("\nDone! Next steps:")
    logger.info("  1. venv/bin/python3.12 scripts/upload_chroma_to_s3.py")
    logger.info("  2. railway up")


if __name__ == "__main__":
    main()
