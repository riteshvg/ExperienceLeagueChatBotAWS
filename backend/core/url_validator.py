"""
Async URL validator with in-process TTL cache.

Drops citations that return a definitive HTTP 404 or 410.
Fail-open: network errors / timeouts keep the citation (corporate proxies
and transient connectivity issues should not silently remove valid sources).

Cache TTLs:
  valid    → 24 h
  invalid  →  1 h  (re-check; EXL occasionally restores pages)
"""

import asyncio
import logging
import time

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT = 3.0
_POS_TTL = 86_400   # 24 h for 200
_NEG_TTL =  3_600   # 1 h for everything else
_MAX_CONCURRENT = 10
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ExLChatbot/1.0)"}

# url → (is_valid: bool, checked_at: float)
_cache: dict[str, tuple[bool, float]] = {}


def _cache_get(url: str) -> bool | None:
    entry = _cache.get(url)
    if not entry:
        return None
    valid, ts = entry
    ttl = _POS_TTL if valid else _NEG_TTL
    if time.monotonic() - ts < ttl:
        return valid
    return None


async def _check_url(client: httpx.AsyncClient, url: str) -> tuple[str, bool]:
    cached = _cache_get(url)
    if cached is not None:
        return url, cached

    try:
        r = await client.head(url, follow_redirects=True)
        valid = r.status_code not in (404, 410)
    except Exception as exc:
        logger.debug(f"URL check error for {url}: {exc}")
        valid = True  # network error / timeout → keep (fail-open)

    _cache[url] = (valid, time.monotonic())
    logger.debug(f"URL check {'✓' if valid else '✗'} [{200 if valid else 'non-200'}] {url}")
    return url, valid


async def filter_valid_citations(citations: list) -> list:
    """Return only citations whose URL resolves to HTTP 200."""
    if not citations:
        return citations

    unique_urls = list(dict.fromkeys(c.get("url", "") for c in citations if c.get("url")))
    sem = asyncio.Semaphore(_MAX_CONCURRENT)

    async def _guarded(client: httpx.AsyncClient, url: str):
        async with sem:
            return await _check_url(client, url)

    async with httpx.AsyncClient(headers=_HEADERS, timeout=_TIMEOUT) as client:
        results = await asyncio.gather(*[_guarded(client, u) for u in unique_urls])

    valid_urls = {url for url, ok in results if ok}
    kept = [c for c in citations if c.get("url", "") in valid_urls]

    removed = len(citations) - len(kept)
    if removed:
        logger.info(f"URL validator: dropped {removed}/{len(citations)} non-200 citations")

    return kept
