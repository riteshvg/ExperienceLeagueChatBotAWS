"""Apply index-time citation metadata enrichment to a ChromaDB collection."""

from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings

from src.utils.citation_metadata import (
    URL_SOURCE_DEAD,
    URL_SOURCE_UNMAPPED,
    URL_SOURCE_VALIDATED,
    enrich_s3_key,
    metadata_to_chroma_fields,
    validate_urls,
)
from src.utils.exl_url_mapper import derive_exl_url, is_specific_url

logger = logging.getLogger(__name__)

DEFAULT_CHROMA_PATH = Path(__file__).parent.parent.parent / "chroma_db"
COLLECTION = "experience_league"
GET_PAGE_SIZE = 500
UPDATE_BATCH = 500


def _iter_chunks(col, *, page_size: int = GET_PAGE_SIZE):
    """Yield (id, metadata) without loading the full collection in one SQL query."""
    offset = 0
    while True:
        page = col.get(include=["metadatas"], limit=page_size, offset=offset)
        ids = page.get("ids") or []
        metas = page.get("metadatas") or []
        if not ids:
            break
        yield from zip(ids, metas)
        offset += len(ids)
        if len(ids) < page_size:
            break


async def enrich_chroma_collection(
    *,
    chroma_path: Path = DEFAULT_CHROMA_PATH,
    dry_run: bool = False,
    product_filter: str | None = None,
    prefix_filter: str | None = None,
    skip_validate: bool = False,
    changed_s3_keys: set[str] | None = None,
) -> None:
    col = chromadb.PersistentClient(
        path=str(chroma_path),
        settings=ChromaSettings(anonymized_telemetry=False),
    ).get_collection(COLLECTION)

    total = col.count()
    logger.info("Collection has %d chunks", total)

    def _matches(meta: dict) -> bool:
        if product_filter and meta.get("product") != product_filter:
            return False
        sk = meta.get("s3_key", "")
        if prefix_filter and prefix_filter not in sk:
            return False
        if changed_s3_keys is not None and sk not in changed_s3_keys:
            return False
        return bool(sk)

    s3_keys: set[str] = set()
    matched = 0
    for _doc_id, meta in _iter_chunks(col):
        if not _matches(meta):
            continue
        matched += 1
        s3_keys.add(meta["s3_key"])

    if changed_s3_keys is not None:
        logger.info(
            "Changed-only mode — %d s3 keys to enrich (from %d changed files)",
            len(s3_keys),
            len(changed_s3_keys),
        )
    logger.info(
        "Enriching %d chunks (%d unique docs)%s%s",
        matched,
        len(s3_keys),
        f" product={product_filter!r}" if product_filter else "",
        f" prefix={prefix_filter!r}" if prefix_filter else "",
    )

    derive_by_key = {sk: derive_exl_url(sk) for sk in s3_keys}
    validate_targets = [u for u in derive_by_key.values() if is_specific_url(u)]

    if skip_validate:
        live_map = {u: True for u in validate_targets}
        logger.info("Skipping HTTP validation")
    else:
        logger.info("Validating %d unique EXL URLs…", len(validate_targets))
        live_map = await validate_urls(validate_targets)

    enriched_by_key = {sk: enrich_s3_key(sk, live_map) for sk in s3_keys}

    stats: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    ids_to_update: list[str] = []
    metas_to_update: list[dict] = []
    updated_total = 0

    def flush_updates() -> None:
        nonlocal ids_to_update, metas_to_update, updated_total
        if dry_run or not ids_to_update:
            ids_to_update, metas_to_update = [], []
            return
        col.update(ids=ids_to_update, metadatas=metas_to_update)
        updated_total += len(ids_to_update)
        ids_to_update, metas_to_update = [], []

    for doc_id, meta in _iter_chunks(col):
        if not _matches(meta):
            continue
        sk = meta.get("s3_key", "")
        if not sk:
            continue

        citation = enriched_by_key.get(sk)
        if not citation:
            continue

        product = meta.get("product", "unknown")
        stats[product][citation.url_source] += 1

        new_fields = metadata_to_chroma_fields(citation)
        if (
            meta.get("repo_path") == new_fields["repo_path"]
            and meta.get("exl_url") == new_fields["exl_url"]
            and meta.get("url") == new_fields["url"]
            and meta.get("url_source") == new_fields["url_source"]
        ):
            continue

        updated = dict(meta)
        updated.update(new_fields)
        ids_to_update.append(doc_id)
        metas_to_update.append(updated)

        if len(ids_to_update) >= UPDATE_BATCH:
            flush_updates()

    flush_updates()

    logger.info("Citation metadata by product:")
    for product in sorted(stats):
        s = stats[product]
        logger.info(
            "  %-35s  validated=%4d  dead=%4d  unmapped=%4d",
            product,
            s.get(URL_SOURCE_VALIDATED, 0),
            s.get(URL_SOURCE_DEAD, 0),
            s.get(URL_SOURCE_UNMAPPED, 0),
        )

    chunks_seen = sum(sum(s.values()) for s in stats.values())
    logger.info(
        "Enrichment complete — %d chunks in collection, %d evaluated, %d metadata updates",
        total,
        chunks_seen,
        updated_total,
    )

    if dry_run:
        return
