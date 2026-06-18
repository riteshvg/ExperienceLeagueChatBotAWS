"""
Topical relevance — gate retrieval results before LLM synthesis.

Ensures query terms (especially topic keywords) appear in doc title, URL path,
or snippet before a chunk is used for answers or shown as a source.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from backend.core.retrieval_refiner import _extract_terms, _lexical_overlap

_TITLE_CLEAN_RE = re.compile(r"\s*\{#[^}]+\}")

# Product / vendor terms — too broad to require as topical matches.
_GENERIC_TERMS = frozenset({
    "adobe", "experience", "platform", "analytics", "customer", "journey",
    "optimizer", "target", "collection", "data", "cloud", "real", "time",
    "aep", "ajo", "cja", "aa", "rtcdp", "exl", "docs", "documentation",
    "different", "various", "types", "what", "are", "the", "for", "about",
})

# Minimum topical score for a doc to be used for answers / sources.
TOPICAL_THRESHOLD = 0.20

# When the query has 2+ significant terms, require at least one in URL path or title.
_MIN_SIGNIFICANT_FOR_URL_CHECK = 2


def significant_terms(query: str) -> list[str]:
    """Topic terms from the user query, excluding generic product vocabulary."""
    terms = _extract_terms(query)
    return [t for t in terms if t.lower() not in _GENERIC_TERMS]


def _clean_title(raw: str) -> str:
    return _TITLE_CLEAN_RE.sub("", raw or "").strip()


def _url_path_text(url: str) -> str:
    if not url:
        return ""
    path = urlparse(url).path.lower()
    return path.replace("-", " ").replace("/", " ")


def doc_relevance_text(doc: dict) -> str:
    meta = doc.get("metadata") or {}
    title = _clean_title(meta.get("title", ""))
    path = meta.get("repo_path") or meta.get("s3_key") or ""
    url = meta.get("url") or ""
    snippet = (doc.get("content") or "")[:1500]
    return f"{title} {path} {url} {snippet}".lower()


def topical_match_score(query: str, doc: dict) -> float:
    """
    Score how well a doc matches the query topic (0–1).

    Combines term overlap with title/snippet text and bonus for URL path hits.
    """
    sig = significant_terms(query)
    terms = sig if sig else _extract_terms(query)
    if not terms:
        return 0.0

    text = doc_relevance_text(doc)
    url_path = _url_path_text((doc.get("metadata") or {}).get("url") or "")

    term_hits = sum(1 for t in terms if t.lower() in text)
    url_hits = sum(
        1 for t in terms
        if t.lower() in url_path or t.lower().replace("_", " ") in url_path
    )

    term_ratio = term_hits / len(terms)
    url_ratio = url_hits / len(terms) if url_path else 0.0
    lex = _lexical_overlap(terms, text)

    # URL/title alignment weighted higher than incidental snippet mentions.
    score = term_ratio * 0.45 + url_ratio * 0.35 + lex * 0.20
    if url_hits > 0:
        score = min(1.0, score + 0.15)
    return min(1.0, score)


def has_direct_url_match(query: str, doc: dict) -> bool:
    """
    True when at least one significant query term appears in the doc URL path or title.
    """
    sig = significant_terms(query)
    if len(sig) < 1:
        return True

    meta = doc.get("metadata") or {}
    title = _clean_title(meta.get("title", "")).lower()
    url_path = _url_path_text(meta.get("url") or "")

    for term in sig:
        lower = term.lower()
        if lower in title or lower in url_path:
            return True
        if lower.replace("-", " ") in url_path:
            return True
    return False


def is_topically_relevant(
    query: str,
    doc: dict,
    *,
    threshold: float = TOPICAL_THRESHOLD,
) -> bool:
    if topical_match_score(query, doc) < threshold:
        return False
    sig = significant_terms(query)
    if len(sig) >= _MIN_SIGNIFICANT_FOR_URL_CHECK and not has_direct_url_match(query, doc):
        return False
    return True


def filter_by_product(docs: list[dict], product: str | None) -> list[dict]:
    if not product:
        return docs
    return [
        d for d in docs
        if (d.get("metadata") or {}).get("product") == product
    ]


def filter_relevant_docs(
    query: str,
    docs: list[dict],
    *,
    threshold: float = TOPICAL_THRESHOLD,
) -> list[dict]:
    """Return docs that pass topical relevance, preserving input order by score."""
    relevant = [d for d in docs if is_topically_relevant(query, d, threshold=threshold)]
    return sorted(relevant, key=lambda d: float(d.get("score", 0.0)), reverse=True)


def assess_retrieval(
    query: str,
    docs: list[dict],
    product_filter: str | None = None,
) -> dict[str, Any]:
    """
    Assess retrieved docs after optional product filtering.

    Returns product_docs, relevant_docs, and diagnostic counts.
    """
    product_docs = filter_by_product(docs, product_filter)
    pool = product_docs if product_filter else docs
    relevant_docs = filter_relevant_docs(query, pool)
    return {
        "product_docs": product_docs,
        "relevant_docs": relevant_docs,
        "topical_scores": {
            _doc_key(d): round(topical_match_score(query, d), 3)
            for d in pool[:10]
        },
    }


def _doc_key(doc: dict) -> str:
    meta = doc.get("metadata") or {}
    return meta.get("s3_key") or meta.get("url") or doc.get("content", "")[:80]
