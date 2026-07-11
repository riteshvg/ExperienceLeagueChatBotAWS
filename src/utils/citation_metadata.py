"""
Index-time citation metadata enrichment.

Experience League URLs are derived, optionally HTTP-validated, and stored on
each chunk. Runtime citation code reads stored metadata only — never re-derives.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Iterable

import httpx

from src.utils.exl_url_mapper import (
    derive_exl_url,
    get_canonical_exl_url,
    is_specific_url,
    repo_from_s3_key,
    repo_path_from_s3_key,
)

_HTTP_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ExLChatbot/1.0)"}
_DEFAULT_TIMEOUT = 8.0
# Experience League publishes no documented rate-limit guidance for its CDN.
# 20 concurrent connections from a single IP is a common bot-detection/WAF
# trip threshold; 5 is a conservative default that stays well under it while
# still validating a large URL set in reasonable time.
_DEFAULT_CONCURRENCY = 5
_MAX_ATTEMPTS = 3
_RETRY_BASE_DELAY_S = 1.0

URL_SOURCE_VALIDATED = "validated"
URL_SOURCE_UNMAPPED = "unmapped"
URL_SOURCE_DEAD = "dead"
# Validation was inconclusive — a timeout, connection error, 429, or 5xx, not
# a confirmed 404/410. Distinct from "dead" so a transient failure (rate
# limiting, a blip) doesn't destroy a correctly-derived URL. exl_url is kept;
# only the citation-display `url` field is cleared until the next successful
# validation pass confirms one way or the other.
URL_SOURCE_UNVALIDATED = "unvalidated"

# Status values returned per-URL by validate_urls().
_STATUS_LIVE = "live"
_STATUS_DEAD = "dead"
_STATUS_UNVALIDATED = "unvalidated"


@dataclass(frozen=True)
class CitationIndexMeta:
    repo_path: str
    exl_url: str
    url: str
    url_source: str


def build_index_metadata(s3_key: str) -> CitationIndexMeta:
    """
    Derive citation fields for indexing. Does not HTTP-validate.
    url/exl_url remain empty until apply_url_validation() marks them live.
    """
    repo_path = repo_path_from_s3_key(s3_key) or ""
    derived = derive_exl_url(s3_key) if s3_key else None

    if not is_specific_url(derived):
        return CitationIndexMeta(
            repo_path=repo_path,
            exl_url="",
            url="",
            url_source=URL_SOURCE_UNMAPPED,
        )

    return CitationIndexMeta(
        repo_path=repo_path,
        exl_url=derived,
        url="",
        url_source="derived",
    )


def apply_url_validation(meta: CitationIndexMeta, status: str) -> CitationIndexMeta:
    """
    Set url fields after an HTTP check.

    status is one of "live", "dead", "unvalidated" (see validate_urls()):
      - live        -> url populated, url_source=validated
      - dead        -> confirmed 404/410 — clear both url and exl_url, the
                        page is genuinely gone
      - unvalidated -> inconclusive (timeout/429/5xx/exception) — preserve
                        exl_url so it survives to the next validation pass
                        without re-deriving; only clear the display `url`
    """
    if not meta.exl_url:
        return meta
    if status == _STATUS_LIVE:
        return CitationIndexMeta(
            repo_path=meta.repo_path,
            exl_url=meta.exl_url,
            url=meta.exl_url,
            url_source=URL_SOURCE_VALIDATED,
        )
    if status == _STATUS_DEAD:
        return CitationIndexMeta(
            repo_path=meta.repo_path,
            exl_url="",
            url="",
            url_source=URL_SOURCE_DEAD,
        )
    return CitationIndexMeta(
        repo_path=meta.repo_path,
        exl_url=meta.exl_url,
        url="",
        url_source=URL_SOURCE_UNVALIDATED,
    )


def metadata_to_chroma_fields(meta: CitationIndexMeta) -> dict[str, str]:
    return {
        "repo_path": meta.repo_path,
        "exl_url": meta.exl_url,
        "url": meta.url,
        "url_source": meta.url_source,
    }


async def validate_urls(urls: Iterable[str], *, concurrency: int = _DEFAULT_CONCURRENCY) -> dict[str, str]:
    """
    Return {url: status} for unique URLs, status in "live" | "dead" | "unvalidated".

    "dead" is reserved for an explicit 404/410 response — a confirmed removal.
    Everything else that isn't a clean success (timeouts, connection errors,
    429, 5xx) is retried up to _MAX_ATTEMPTS times with linear backoff before
    falling back to "unvalidated" — never "dead". A transient failure must
    never be indistinguishable from a confirmed-gone page.
    """
    unique = list(dict.fromkeys(u for u in urls if u))
    if not unique:
        return {}

    sem = asyncio.Semaphore(concurrency)
    results: dict[str, str] = {}

    async def _check(client: httpx.AsyncClient, url: str) -> None:
        async with sem:
            for attempt in range(1, _MAX_ATTEMPTS + 1):
                try:
                    r = await client.head(url, follow_redirects=True)
                except Exception:
                    if attempt < _MAX_ATTEMPTS:
                        await asyncio.sleep(_RETRY_BASE_DELAY_S * attempt)
                        continue
                    results[url] = _STATUS_UNVALIDATED
                    return

                if r.status_code in (404, 410):
                    results[url] = _STATUS_DEAD
                    return
                if r.status_code == 429 or r.status_code >= 500:
                    if attempt < _MAX_ATTEMPTS:
                        await asyncio.sleep(_RETRY_BASE_DELAY_S * attempt)
                        continue
                    results[url] = _STATUS_UNVALIDATED
                    return
                results[url] = _STATUS_LIVE
                return

    async with httpx.AsyncClient(headers=_HTTP_HEADERS, timeout=_DEFAULT_TIMEOUT) as client:
        await asyncio.gather(*[_check(client, u) for u in unique])

    return results


def enrich_s3_key(s3_key: str, validation_map: dict[str, str]) -> CitationIndexMeta:
    """Build index metadata and apply precomputed HTTP validation results."""
    base = build_index_metadata(s3_key)
    if not base.exl_url:
        return base
    return apply_url_validation(base, validation_map.get(base.exl_url, _STATUS_UNVALIDATED))


@dataclass(frozen=True)
class ValidationRow:
    product: str
    repo: str
    repo_path: str
    exl_url: str
    status: str  # live | dead | unmapped | unvalidated


def validation_row(s3_key: str, product: str, validation_map: dict[str, str]) -> ValidationRow:
    repo = repo_from_s3_key(s3_key) or ""
    repo_path = repo_path_from_s3_key(s3_key) or ""
    derived = derive_exl_url(s3_key) if s3_key else None

    if not is_specific_url(derived):
        return ValidationRow(product, repo, repo_path, "", "unmapped")

    status = validation_map.get(derived, _STATUS_UNVALIDATED)
    return ValidationRow(product, repo, repo_path, derived, status)


def get_canonical_from_repo_path(repo_path: str, repo: str) -> str | None:
    """Public alias for index-time resolver (repo-relative path + GitHub repo slug)."""
    return get_canonical_exl_url(repo_path, repo)
