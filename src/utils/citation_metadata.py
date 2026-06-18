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
_DEFAULT_CONCURRENCY = 20

URL_SOURCE_VALIDATED = "validated"
URL_SOURCE_UNMAPPED = "unmapped"
URL_SOURCE_DEAD = "dead"


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


def apply_url_validation(meta: CitationIndexMeta, is_live: bool) -> CitationIndexMeta:
    """Set url fields after HTTP check. Only live URLs are stored for citations."""
    if not meta.exl_url:
        return meta
    if is_live:
        return CitationIndexMeta(
            repo_path=meta.repo_path,
            exl_url=meta.exl_url,
            url=meta.exl_url,
            url_source=URL_SOURCE_VALIDATED,
        )
    return CitationIndexMeta(
        repo_path=meta.repo_path,
        exl_url="",
        url="",
        url_source=URL_SOURCE_DEAD,
    )


def metadata_to_chroma_fields(meta: CitationIndexMeta) -> dict[str, str]:
    return {
        "repo_path": meta.repo_path,
        "exl_url": meta.exl_url,
        "url": meta.url,
        "url_source": meta.url_source,
    }


async def validate_urls(urls: Iterable[str], *, concurrency: int = _DEFAULT_CONCURRENCY) -> dict[str, bool]:
    """Return {url: is_live} for unique URLs."""
    unique = list(dict.fromkeys(u for u in urls if u))
    if not unique:
        return {}

    sem = asyncio.Semaphore(concurrency)
    results: dict[str, bool] = {}

    async def _check(client: httpx.AsyncClient, url: str) -> None:
        async with sem:
            try:
                r = await client.head(url, follow_redirects=True)
                results[url] = r.status_code not in (404, 410)
            except Exception:
                results[url] = False

    async with httpx.AsyncClient(headers=_HTTP_HEADERS, timeout=_DEFAULT_TIMEOUT) as client:
        await asyncio.gather(*[_check(client, u) for u in unique])

    return results


def enrich_s3_key(s3_key: str, live_urls: dict[str, bool]) -> CitationIndexMeta:
    """Build index metadata and apply precomputed HTTP validation results."""
    base = build_index_metadata(s3_key)
    if not base.exl_url:
        return base
    return apply_url_validation(base, live_urls.get(base.exl_url, False))


@dataclass(frozen=True)
class ValidationRow:
    product: str
    repo: str
    repo_path: str
    exl_url: str
    status: str  # live | dead | unmapped


def validation_row(s3_key: str, product: str, live_urls: dict[str, bool]) -> ValidationRow:
    repo = repo_from_s3_key(s3_key) or ""
    repo_path = repo_path_from_s3_key(s3_key) or ""
    derived = derive_exl_url(s3_key) if s3_key else None

    if not is_specific_url(derived):
        return ValidationRow(product, repo, repo_path, "", "unmapped")

    status = "live" if live_urls.get(derived, False) else "dead"
    return ValidationRow(product, repo, repo_path, derived, status)


def get_canonical_from_repo_path(repo_path: str, repo: str) -> str | None:
    """Public alias for index-time resolver (repo-relative path + GitHub repo slug)."""
    return get_canonical_exl_url(repo_path, repo)
