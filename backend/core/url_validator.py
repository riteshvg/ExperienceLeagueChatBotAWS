"""
Async URL validator with in-memory TTL cache.

Validates citation URLs before they're sent to the client.
404s are filtered; timeouts / server errors keep the benefit of the doubt.
"""

import asyncio
import logging
import time
from typing import Sequence

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT = 3.0       # seconds per request
_CACHE_TTL = 3600    # cache results for 1 hour
_MAX_CONCURRENT = 10

# url → (is_valid, expires_at)
_cache: dict[str, tuple[bool, float]] = {}


def _cache_get(url: str) -> bool | None:
    entry = _cache.get(url)
    if entry and entry[1] > time.monotonic():
        return entry[0]
    return None


def _cache_set(url: str, valid: bool) -> None:
    _cache[url] = (valid, time.monotonic() + _CACHE_TTL)


async def _check_url(client: httpx.AsyncClient, url: str) -> tuple[str, bool]:
    cached = _cache_get(url)
    if cached is not None:
        return url, cached

    try:
        r = await client.head(url, follow_redirects=True)
        valid = r.status_code != 404 and r.status_code != 410
    except Exception:
        valid = True  # network error → keep

    _cache_set(url, valid)
    logger.debug(f"URL check {'✓' if valid else '✗'} {url}")
    return url, valid


async def filter_valid_citations(citations: list) -> list:
    """Return citations whose URLs respond with something other than 404/410."""
    if not citations:
        return citations

    urls = [c.get("url", "") for c in citations]
    unique_urls = list(dict.fromkeys(u for u in urls if u))

    sem = asyncio.Semaphore(_MAX_CONCURRENT)

    async def _guarded(client: httpx.AsyncClient, url: str):
        async with sem:
            return await _check_url(client, url)

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        results = await asyncio.gather(*[_guarded(client, u) for u in unique_urls])

    valid_urls = {url for url, ok in results if ok}
    kept = [c for c in citations if c.get("url", "") in valid_urls]

    removed = len(citations) - len(kept)
    if removed:
        logger.info(f"URL validator: removed {removed} dead citation(s) from {len(citations)}")

    return kept
