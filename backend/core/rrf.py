"""Reciprocal rank fusion for combining ranked document lists (dense + BM25)."""

from __future__ import annotations

_DEFAULT_K = 60


def _doc_key(doc: dict) -> str:
    meta = doc.get("metadata") or {}
    return meta.get("s3_key") or meta.get("url") or doc.get("content", "")[:80]


def reciprocal_rank_fusion(
    ranked_lists: list[list[dict]],
    *,
    k: int = _DEFAULT_K,
) -> list[dict]:
    """
    Fuse multiple already-ranked (best-first) document lists into one ranked
    list using RRF: score(d) = sum(1 / (k + rank_i)) over every list d appears
    in (1-indexed rank). Rank-based rather than raw-score-based fusion, so it
    needs no cross-list score normalization between e.g. cosine similarity and
    BM25 magnitude — only relative order within each list matters.

    Each returned doc carries an added "rrf_score" key; the original "score"
    field (embedding or BM25 score of whichever list first produced the doc)
    is left untouched for downstream consumers (topical gate, citations) that
    key off it.
    """
    fused: dict[str, float] = {}
    doc_by_key: dict[str, dict] = {}

    for docs in ranked_lists:
        for rank, doc in enumerate(docs, start=1):
            key = _doc_key(doc)
            fused[key] = fused.get(key, 0.0) + 1.0 / (k + rank)
            if key not in doc_by_key:
                doc_by_key[key] = doc

    ordered_keys = sorted(fused, key=lambda key: fused[key], reverse=True)
    results = []
    for key in ordered_keys:
        doc = dict(doc_by_key[key])
        doc["rrf_score"] = fused[key]
        results.append(doc)
    return results
