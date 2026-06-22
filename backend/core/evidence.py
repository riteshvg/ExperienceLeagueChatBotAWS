"""
Retrieval evidence metadata for chat responses.

Isolated from RAG pipeline logic — builds structured evidence payloads
for the frontend without changing retrieval thresholds or routing.
"""

from __future__ import annotations

import re
from typing import Any

from src.utils.exl_url_mapper import is_specific_url, resolve_doc_url

# Mirrors RAGPipeline._CITATION_SCORE_THRESHOLD — used for labelling only.
CITED_SCORE_THRESHOLD = 0.70


def _clean_title(raw: str) -> str:
    return re.sub(r"\s*\{#[^}]+\}", "", raw or "").strip()


def _source_from_doc(doc: dict, cited: bool, topical_score: float | None = None) -> dict[str, Any] | None:
    meta = doc.get("metadata", {})
    url = resolve_doc_url(meta, doc.get("content", "")) or meta.get("url", "")
    if not is_specific_url(url):
        return None
    src: dict[str, Any] = {
        "url": url,
        "repo_path": meta.get("repo_path", ""),
        "title": _clean_title(meta.get("title", "")) or "Documentation",
        "product": meta.get("product", ""),
        "score": round(float(doc.get("score", 0.0)), 3),
        "cited": cited,
    }
    if topical_score is not None:
        src["topical_score"] = round(topical_score, 3)
    return src


def _dedupe_sources(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for src in sources:
        url = src.get("url", "")
        if not url or url in seen:
            continue
        seen.add(url)
        out.append(src)
    return out


def build_numbered_context(raw_docs: list[dict]) -> tuple[str, list[dict[str, Any]]]:
    """
    Build LLM context with consecutive [1]…[k] markers only on chunks that have linkable URLs.

    Unlinkable chunks are still included (unnumbered) for grounding but should not be cited.
    """
    parts: list[str] = []
    index: list[dict[str, Any]] = []
    num = 0
    for doc in raw_docs:
        meta = doc.get("metadata") or {}
        url = resolve_doc_url(meta, doc.get("content", "")) or meta.get("url", "")
        content = doc.get("content", "")
        if is_specific_url(url):
            num += 1
            parts.append(f"[{num}] {content}")
            index.append({
                "url": url,
                "title": _clean_title(meta.get("title", "")) or "Documentation",
                "product": meta.get("product", ""),
            })
        elif content.strip():
            parts.append(content)
    return "\n\n---\n\n".join(parts), index


def build_context_index(raw_docs: list[dict]) -> list[dict[str, Any]]:
    """Citation index aligned with [1], [2], … markers sent to the LLM."""
    _, index = build_numbered_context(raw_docs)
    return index


def _evidence_level(top_score: float, source_count: int) -> str:
    if source_count == 0 or top_score < 0.25:
        return "none"
    if top_score < 0.30:
        return "weak"
    if top_score < 0.55:
        return "moderate"
    return "strong"


def _grounding_level(evidence_level: str, citation_count: int) -> str:
    if evidence_level == "none":
        return "insufficient"
    if evidence_level == "strong" and citation_count >= 1:
        return "documented"
    if evidence_level in {"moderate", "strong"}:
        return "partial"
    return "inferred"


def _match_label(evidence_level: str) -> str:
    return {
        "none": "None",
        "weak": "Low",
        "moderate": "Moderate",
        "strong": "Strong",
    }.get(evidence_level, "Unknown")


def _grounding_label(grounding_level: str) -> str:
    return {
        "documented": "Directly documented",
        "partial": "Partially documented",
        "inferred": "Inferred from related docs",
        "insufficient": "Insufficient evidence",
    }.get(grounding_level, grounding_level)


def build_evidence(
    raw_docs: list[dict],
    product_filter: str | None = None,
    failure_reason: str | None = None,
    related_docs: list[dict] | None = None,
    refinement: dict[str, Any] | None = None,
    topical_scores: dict[str, float] | None = None,
) -> dict[str, Any]:
    """
    Build evidence payload from retrieved docs.

    raw_docs: docs that passed topical relevance (used for LLM context)
    related_docs: optional lower-relevance docs for blocked responses
    topical_scores: optional doc-key → topical match score map
    """
    docs_for_sources = raw_docs if raw_docs else (related_docs or [])

    sources: list[dict[str, Any]] = []
    for doc in docs_for_sources:
        score = float(doc.get("score", 0.0))
        cited = score >= CITED_SCORE_THRESHOLD
        meta = doc.get("metadata") or {}
        doc_key = meta.get("s3_key") or meta.get("url") or doc.get("content", "")[:80]
        topical = (topical_scores or {}).get(doc_key)
        src = _source_from_doc(doc, cited=cited, topical_score=topical)
        if src:
            if failure_reason in ("no_direct_match", "no_retrieval", "off_topic") and topical is not None:
                src["score"] = round(topical, 3)
            sources.append(src)
    sources = _dedupe_sources(sources)

    # Blocked responses may include related docs for transparency — never treat as cited.
    if failure_reason in ("no_retrieval", "no_direct_match", "off_topic"):
        for src in sources:
            src["cited"] = False

    # Score evidence from displayable sources when available — avoids inflating
    # confidence with high-similarity chunks that have no valid URL.
    source_count = len(sources)
    if sources:
        top_score = max(float(s.get("score", 0.0)) for s in sources)
        scores = [float(s.get("score", 0.0)) for s in sources]
    else:
        top_score = max((float(d.get("score", 0.0)) for d in docs_for_sources), default=0.0)
        scores = [float(d.get("score", 0.0)) for d in docs_for_sources]

    avg_score = round(sum(scores) / len(scores), 3) if scores else 0.0
    top_score = round(top_score, 3)

    citation_count = sum(1 for s in sources if s.get("cited"))
    level = _evidence_level(top_score, source_count)
    grounding = _grounding_level(level, citation_count)

    if failure_reason == "no_retrieval":
        level, grounding = "none", "insufficient"
        citation_count = 0
    elif failure_reason == "no_direct_match":
        level = "weak" if sources else "none"
        grounding = "insufficient"
        citation_count = 0
    elif failure_reason == "off_topic":
        level = "weak" if source_count else "none"
        grounding = "inferred"
        citation_count = 0

    banner: str | None = None
    if failure_reason == "no_retrieval":
        banner = (
            "Not enough evidence — no documentation matched strongly enough to answer confidently."
        )
    elif failure_reason == "no_direct_match":
        banner = (
            "No directly matching documentation found — retrieved pages do not cover "
            "this specific topic in our indexed docs."
        )
    elif failure_reason == "off_topic":
        banner = "Low relevance — retrieved documentation is a weak match for this question."
    elif grounding == "partial":
        banner = "Partially documented — verify steps against the sources below before implementing."
    elif grounding == "inferred":
        banner = "Limited documentation — parts of this answer may be inferred from related material."

    if failure_reason != "no_direct_match" and refinement and refinement.get("refinement_applied"):
        neighbor_hint = ""
        neighbors = refinement.get("refinement_neighbors") or []
        if neighbors:
            neighbor_hint = f" (aligned to: {neighbors[0]})"
        banner = (
            f"Matched using documentation-aligned search{neighbor_hint}."
        )

    payload: dict[str, Any] = {
        "source_count": source_count,
        "citation_count": citation_count,
        "top_score": top_score,
        "avg_score": avg_score,
        "product_filter": product_filter,
        "evidence_level": level,
        "grounding_level": grounding,
        "match_label": _match_label(level),
        "grounding_label": _grounding_label(grounding),
        "failure_reason": failure_reason,
        "banner": banner,
        "sources": sources,
        "context_index": build_context_index(raw_docs),
    }
    if refinement:
        payload["refinement"] = refinement
    return payload
