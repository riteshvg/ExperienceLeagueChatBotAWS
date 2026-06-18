"""
Retrieval refinement — recover from weak or empty first-pass retrieval.

When the initial search returns nothing (or only low-confidence matches),
probe near-neighbor chunks in ChromaDB, assess the vocabulary / filter gap,
and retry with search queries anchored to neighbor document titles.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

_OFF_TOPIC_THRESHOLD = 0.25
_REFINEMENT_MIN_SCORE = 0.20
_PROBE_NEIGHBORS = 15
_MAX_REFINED_QUERIES = 4

_STOPWORDS = frozenset({
    "what", "how", "does", "the", "and", "for", "with", "via", "from", "that",
    "this", "are", "can", "you", "your", "about", "when", "where", "which",
    "into", "using", "use", "set", "get", "have", "has", "was", "were", "will",
    "should", "would", "could", "their", "they", "them", "then", "than", "also",
    "just", "only", "not", "but", "all", "any", "our", "its", "it's", "is",
    "a", "an", "to", "of", "in", "on", "at", "by", "or", "as", "be", "do",
    "i", "me", "my", "we", "if", "so", "up", "out", "no", "yes",
})

_CAMEL_RE = re.compile(r"[a-z]+(?:[A-Z][a-z0-9]*)+")
_TITLE_CLEAN_RE = re.compile(r"\s*\{#[^}]+\}")


@dataclass
class RefinementResult:
    applied: bool = False
    gap_reasons: list[str] = field(default_factory=list)
    original_search: str = ""
    refined_searches: list[str] = field(default_factory=list)
    winning_search: str | None = None
    neighbor_titles: list[str] = field(default_factory=list)
    initial_top_score: float = 0.0
    refined_top_score: float = 0.0


def _top_score(docs: list[dict]) -> float:
    if not docs:
        return 0.0
    return max(float(d.get("score", 0.0)) for d in docs)


def _doc_key(doc: dict) -> str:
    meta = doc.get("metadata") or {}
    return meta.get("s3_key") or meta.get("url") or doc.get("content", "")[:80]


def _clean_title(raw: str) -> str:
    return _TITLE_CLEAN_RE.sub("", raw or "").strip()


_SHORT_ALLOW = frozenset({"sdk", "web", "aep", "ajo", "cja", "api", "xdm", "fpid", "ecid"})


def _extract_terms(query: str) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()

    for match in _CAMEL_RE.findall(query):
        token = match.strip()
        if token.lower() not in seen:
            seen.add(token.lower())
            terms.append(token)

    for word in re.findall(r"[A-Za-z0-9][A-Za-z0-9._-]{2,}", query):
        lower = word.lower()
        if lower in _STOPWORDS or lower in seen:
            continue
        if len(word) <= 3 and word.lower() not in _SHORT_ALLOW and not word.isupper():
            continue
        seen.add(lower)
        terms.append(word)

    return terms[:8]


def _title_keywords(title: str) -> list[str]:
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9+.-]*", title.lower())
    return [w for w in words if w not in _STOPWORDS and len(w) > 2][:6]


def _merge_docs(doc_lists: list[list[dict]]) -> list[dict]:
    best: dict[str, dict] = {}
    for docs in doc_lists:
        for doc in docs:
            key = _doc_key(doc)
            if key not in best or float(doc.get("score", 0)) > float(best[key].get("score", 0)):
                best[key] = doc
    merged = sorted(best.values(), key=lambda d: float(d.get("score", 0)), reverse=True)
    return merged


def _assess_gap(
    *,
    initial_docs: list[dict],
    filtered_neighbors: list[dict],
    unfiltered_neighbors: list[dict],
    similarity_threshold: float,
    product_filter: str | None,
) -> list[str]:
    reasons: list[str] = []
    initial_top = _top_score(initial_docs)
    filtered_top = _top_score(filtered_neighbors)
    unfiltered_top = _top_score(unfiltered_neighbors)

    if not initial_docs:
        reasons.append("no_docs_above_threshold")
    elif initial_top < _OFF_TOPIC_THRESHOLD:
        reasons.append("low_similarity_matches")

    if product_filter and unfiltered_top > filtered_top + 0.05:
        reasons.append("product_filter_excluded_stronger_neighbors")

    if unfiltered_top > initial_top + 0.08:
        reasons.append("documentation_vocabulary_mismatch")

    if initial_top < similarity_threshold:
        reasons.append("below_retrieval_threshold")

    return reasons or ["weak_retrieval"]


def _lexical_overlap(terms: list[str], text: str) -> float:
    if not terms or not text:
        return 0.0
    text_lower = text.lower()
    hits = sum(1 for term in terms if term.lower() in text_lower)
    score = hits / len(terms)
    # Strong bonus when technical identifiers appear verbatim (e.g. identityMap).
    for term in terms:
        if _CAMEL_RE.fullmatch(term) and term in text:
            score += 0.2
    return min(score, 1.0)


def _rank_neighbors_for_refinement(user_query: str, terms: list[str], neighbors: list[dict]) -> list[dict]:
    """Re-rank near neighbors: embedding score + lexical overlap with the user question."""

    def _composite(doc: dict) -> float:
        meta = doc.get("metadata") or {}
        title = _clean_title(meta.get("title", ""))
        snippet = (doc.get("content") or "")[:1000]
        embed = float(doc.get("score", 0.0))
        lex = _lexical_overlap(terms, f"{title} {snippet} {user_query}")
        # When all embedding scores are weak, trust lexical alignment more.
        embed_weight = 0.55 if embed >= 0.15 else 0.25
        return embed * embed_weight + lex * (1.0 - embed_weight)

    return sorted(neighbors, key=_composite, reverse=True)


def _probe_neighbors(
    retriever,
    user_query: str,
    search_query: str,
) -> list[dict]:
    """Gather near neighbors using multiple phrasings of the same question."""
    pools: list[list[dict]] = []
    terms_query = " ".join(_extract_terms(user_query))
    for q in dict.fromkeys([user_query, search_query, terms_query]):
        if not q or not q.strip():
            continue
        pools.append(
            retriever.retrieve(
                q,
                n_results=_PROBE_NEIGHBORS,
                similarity_threshold=0.0,
                where=None,
            )
        )
    return _merge_docs(pools)


def _build_refined_queries(
    user_query: str,
    search_query: str,
    neighbors: list[dict],
    terms: list[str],
) -> list[str]:
    """Build search queries anchored to near-neighbor document titles."""
    if not terms:
        terms = _extract_terms(user_query)
    if not terms:
        terms = _extract_terms(search_query)

    queries: list[str] = []
    seen: set[str] = set()

    def _add(q: str) -> None:
        q = " ".join(q.split()).strip()
        if not q or len(q) < 8:
            return
        key = q.lower()
        if key in seen:
            return
        seen.add(key)
        queries.append(q)

    ranked = _rank_neighbors_for_refinement(user_query, terms, neighbors)

    for doc in ranked[:6]:
        meta = doc.get("metadata") or {}
        title = _clean_title(meta.get("title", ""))
        product = meta.get("product", "")
        if not title:
            continue

        title_kw = _title_keywords(title)
        overlap = _lexical_overlap(terms, title)
        if overlap < 0.08 and float(doc.get("score", 0)) < 0.12:
            continue

        if terms:
            _add(" ".join(terms + title_kw))
            _add(f"{' '.join(terms)} {title}")
        else:
            _add(title)

        if product and title_kw:
            _add(f"{' '.join(title_kw)} {product}")

    for doc in ranked[:3]:
        title = _clean_title((doc.get("metadata") or {}).get("title", ""))
        if title and _lexical_overlap(terms, title) >= 0.08:
            _add(title)

    return queries[:_MAX_REFINED_QUERIES]


def _technical_term_coverage(terms: list[str], text: str) -> float:
    """Fraction of camelCase identifiers from the query found verbatim in the doc."""
    camel_terms = [t for t in terms if _CAMEL_RE.fullmatch(t)]
    if not camel_terms:
        return 1.0
    hits = sum(1 for term in camel_terms if term in text)
    return hits / len(camel_terms)


def _composite_doc_score(doc: dict, terms: list[str], user_query: str, *, refinement: bool = True) -> float:
    meta = doc.get("metadata") or {}
    title = _clean_title(meta.get("title", ""))
    snippet = (doc.get("content") or "")[:2500]
    doc_text = f"{title} {snippet}"
    embed = float(doc.get("score", 0.0))
    lex = _lexical_overlap(terms, f"{doc_text} {user_query}")
    tech = _technical_term_coverage(terms, doc_text)
    if refinement:
        base = embed * 0.35 + lex * 0.65
        if tech < 1.0:
            base *= 0.25 + 0.75 * tech
        return base
    embed_weight = 0.5 if embed >= 0.2 else 0.3
    return embed * embed_weight + lex * (1.0 - embed_weight)


def _needs_refinement(docs: list[dict]) -> bool:
    if not docs:
        return True
    return _top_score(docs) < _OFF_TOPIC_THRESHOLD


def retrieve_with_refinement(
    retriever,
    search_query: str,
    user_query: str,
    *,
    n_results: int,
    similarity_threshold: float,
    product_filter: str | None,
    where_filter: dict | None,
) -> tuple[list[dict], RefinementResult | None]:
    """
    First-pass retrieval; on weak/empty results, refine using near-neighbor titles.
    Returns (docs, refinement_metadata).
    """
    initial = retriever.retrieve(
        search_query,
        n_results=n_results,
        similarity_threshold=similarity_threshold,
        where=where_filter,
    )

    meta = RefinementResult(
        original_search=search_query,
        initial_top_score=_top_score(initial),
    )

    if not _needs_refinement(initial):
        return initial, None

    unfiltered_neighbors = _probe_neighbors(retriever, user_query, search_query)
    filtered_neighbors: list[dict] = []
    if where_filter:
        filtered_neighbors = retriever.retrieve(
            search_query,
            n_results=_PROBE_NEIGHBORS,
            similarity_threshold=0.0,
            where=where_filter,
        )

    meta.gap_reasons = _assess_gap(
        initial_docs=initial,
        filtered_neighbors=filtered_neighbors,
        unfiltered_neighbors=unfiltered_neighbors,
        similarity_threshold=similarity_threshold,
        product_filter=product_filter,
    )
    terms = _extract_terms(user_query)
    ranked_neighbors = _rank_neighbors_for_refinement(user_query, terms, unfiltered_neighbors)
    meta.neighbor_titles = [
        _clean_title((d.get("metadata") or {}).get("title", ""))
        for d in ranked_neighbors[:5]
        if _clean_title((d.get("metadata") or {}).get("title", ""))
    ]

    neighbor_pool = _merge_docs([unfiltered_neighbors, filtered_neighbors, initial])
    refined_queries = _build_refined_queries(user_query, search_query, neighbor_pool, terms)
    meta.refined_searches = refined_queries

    if not refined_queries:
        logger.info("Retrieval refinement: no neighbor-anchored queries generated")
        return initial if initial else [], meta

    doc_sources: dict[str, str] = {}
    retry_batches: list[list[dict]] = []

    for rq in refined_queries:
        docs = retriever.retrieve(
            rq,
            n_results=n_results,
            similarity_threshold=_REFINEMENT_MIN_SCORE,
            where=None,
        )
        if not docs:
            continue
        retry_batches.append(docs)
        for doc in docs:
            doc_sources[_doc_key(doc)] = rq

    merged = _merge_docs(retry_batches)
    refined_docs = sorted(
        merged,
        key=lambda d: _composite_doc_score(d, terms, user_query),
        reverse=True,
    )[:n_results]

    embed_top = _top_score(refined_docs)
    composite_top = _composite_doc_score(refined_docs[0], terms, user_query) if refined_docs else 0.0
    meta.refined_top_score = embed_top

    if refined_docs and (embed_top >= _OFF_TOPIC_THRESHOLD or composite_top >= 0.22):
        meta.applied = True
        meta.winning_search = doc_sources.get(_doc_key(refined_docs[0]))
        logger.info(
            "Retrieval refinement succeeded: %s → %s (%.3f → %.3f composite=%.3f)",
            search_query[:60],
            (meta.winning_search or "")[:60],
            meta.initial_top_score,
            embed_top,
            composite_top,
        )
        return refined_docs, meta

    logger.info(
        "Retrieval refinement did not reach confidence threshold (best=%.3f)",
        meta.refined_top_score,
    )
    return initial if initial else [], meta


def refinement_to_evidence_fields(refinement: RefinementResult | None) -> dict[str, Any]:
    if not refinement or not refinement.applied:
        return {}
    return {
        "refinement_applied": True,
        "refinement_search": refinement.winning_search,
        "refinement_gap": ", ".join(refinement.gap_reasons),
        "refinement_neighbors": refinement.neighbor_titles[:3],
    }
