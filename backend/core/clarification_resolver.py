"""
Clarification resolver — suggest rephrased questions when retrieval is blocked.

When the topical gate or product filter rejects a query but near-neighbor docs exist,
build user-facing options so the user can pick the intended topic and retry retrieval
with explicit product / query routing (no index retagging required).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from backend.core.retrieval_refiner import (
    RefinementResult,
    _clean_title,
    _doc_key,
    _extract_terms,
    _merge_docs,
    _probe_neighbors,
    _rank_neighbors_for_refinement,
)
from backend.core.topical_relevance import significant_terms
from backend.core.query_keywords import TERM_SYNONYMS
from src.utils.exl_url_mapper import resolve_doc_url

_MAX_OPTIONS = 4
_MIN_NEIGHBOR_SCORE = 0.02


def _term_expansion(acronym: str) -> str | None:
    syns = TERM_SYNONYMS.get(acronym.lower())
    return syns[0] if syns else None


_GENESIS_TEMPLATE = (
    "I don't have specific documentation in my current context about **{topic}**. "
    "To provide you with accurate and complete information about this topic, "
    "please pick an option from the below."
)

_QUESTION_PREFIX_RE = re.compile(
    r"^(?:how\s+(?:do(?:\s+i)?|to|can\s+i)\s+|what\s+(?:is|are)\s+|"
    r"where\s+(?:do\s+i|can\s+i)\s+|when\s+(?:do\s+i|should\s+i)\s+|"
    r"why\s+(?:do|does|is)\s+|can\s+(?:you|i)\s+|could\s+(?:you|i)\s+|"
    r"please\s+|tell\s+me\s+(?:about|how)\s+|walk\s+me\s+through\s+|explain\s+)",
    re.IGNORECASE,
)

_ACTION_PREFIX_RE = re.compile(
    r"^(?:implement|install|configure|set\s+up|setup|create|use|enable|add|deploy)\s+",
    re.IGNORECASE,
)

_FILLER_TERMS = frozenset({"work", "works", "working", "mean", "means", "help"})


@dataclass
class ClarificationOption:
    id: str
    label: str
    query: str
    product: str
    doc_title: str
    preview_url: str
    doc_anchor_s3_key: str = ""
    similarity_score: float = 0.0
    match_strength: str = "Weak"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "query": self.query,
            "product": self.product,
            "doc_title": self.doc_title,
            "preview_url": self.preview_url,
            "doc_anchor_s3_key": self.doc_anchor_s3_key,
            "similarity_score": self.similarity_score,
            "match_strength": self.match_strength,
        }


@dataclass
class ClarificationResult:
    genesis: str
    options: list[ClarificationOption] = field(default_factory=list)
    original_query: str = ""
    blocked_reason: str = ""
    intent_summary: str = ""

    @property
    def has_options(self) -> bool:
        return len(self.options) > 0

    def to_event_payload(self) -> dict[str, Any]:
        return {
            "type": "clarification",
            "genesis": self.genesis,
            "original_query": self.original_query,
            "blocked_reason": self.blocked_reason,
            "intent_summary": self.intent_summary,
            "options": [o.to_dict() for o in self.options],
        }


def _expand_query_terms(query: str) -> list[str]:
    terms = _extract_terms(query)
    expanded: list[str] = []
    seen: set[str] = set()
    for term in terms:
        lower = term.lower()
        if lower not in seen:
            seen.add(lower)
            expanded.append(term)
        repl = _term_expansion(lower)
        if repl and repl.lower() not in seen:
            seen.add(repl.lower())
            expanded.append(repl)
    return expanded


def _format_topic_phrase(query: str, product_intent: str | None) -> str:
    """Build a natural topic phrase for the clarification opening."""
    text = _QUESTION_PREFIX_RE.sub("", query.strip())
    text = _ACTION_PREFIX_RE.sub("", text)
    text = re.sub(r"[?.!]+$", "", text).strip()
    text = re.sub(r"\s+work\s+", " ", text, flags=re.IGNORECASE).strip()

    sig = [t for t in significant_terms(query) if t.lower() not in _FILLER_TERMS]
    if not text or len(text.split()) < 2:
        text = " ".join(sig) if sig else query.strip().rstrip("?.!")

    if product_intent and product_intent.lower() not in text.lower():
        text = f"{text} in {product_intent}"

    words = text.split()
    if words and not (words[0].isupper() and len(words[0]) <= 5):
        words[0] = words[0].lower()
        text = " ".join(words)

    return text or "this topic"


def _build_genesis(query: str, product_intent: str | None) -> str:
    topic = _format_topic_phrase(query, product_intent)
    text = _GENESIS_TEMPLATE.format(topic=topic)

    expansions = [
        f"{k.upper()} → {v}"
        for k in TERM_SYNONYMS
        if re.search(rf"\b{re.escape(k)}\b", query, re.IGNORECASE)
        for v in [(_term_expansion(k) or "")]
        if v
    ]
    if expansions:
        text += f"\n\n({'; '.join(expansions)})"
    return text


def _match_strength(score: float) -> tuple[float, str]:
    """Map embedding similarity to a user-facing strength label."""
    rounded = round(score, 3)
    if score >= 0.55:
        return rounded, "Strong"
    if score >= 0.30:
        return rounded, "Moderate"
    if score >= 0.25:
        return rounded, "Low"
    return rounded, "Weak"


def _option_label(title: str, product: str) -> str:
    title_clean = _clean_title(title)
    short_product = product.replace("Adobe ", "") if product else "Adobe docs"
    if len(title_clean) > 55:
        title_clean = title_clean[:52] + "…"
    return f"{title_clean} ({short_product})"


def _option_query(title: str, product: str) -> str:
    title_clean = _clean_title(title)
    product_name = product or "Adobe Experience Cloud"
    lower = title_clean.lower()
    if "extension" in lower or "overview" in lower:
        return f"How do I install and configure {title_clean}?"
    if "tutorial" in lower or "learn" in lower:
        return f"Walk me through {title_clean}"
    return f"How do I implement {title_clean} in {product_name}?"


def _doc_preview_url(doc: dict) -> str:
    meta = doc.get("metadata") or {}
    return resolve_doc_url(meta, doc.get("content", "")) or meta.get("url", "") or ""


def _dedupe_neighbor_docs(docs: list[dict]) -> list[dict]:
    best: dict[str, dict] = {}
    for doc in docs:
        meta = doc.get("metadata") or {}
        key = meta.get("s3_key") or meta.get("url") or _doc_key(doc)
        if not key:
            continue
        if key not in best or float(doc.get("score", 0)) > float(best[key].get("score", 0)):
            best[key] = doc
    return sorted(best.values(), key=lambda d: float(d.get("score", 0)), reverse=True)


def _expanded_search_queries(user_query: str, search_query: str) -> list[str]:
    """Build alternate probe queries — acronym expansion and term-only variants."""
    queries: list[str] = []
    seen: set[str] = set()

    def _add(q: str) -> None:
        q = " ".join(q.split()).strip()
        key = q.lower()
        if q and key not in seen:
            seen.add(key)
            queries.append(q)

    _add(user_query)
    _add(search_query)

    expanded_text = user_query
    for acr in TERM_SYNONYMS:
        repl = _term_expansion(acr)
        if repl:
            expanded_text = re.sub(
                rf"\b{re.escape(acr)}\b", repl, expanded_text, flags=re.IGNORECASE,
            )
    _add(expanded_text)

    terms = _expand_query_terms(user_query)
    if terms:
        _add(" ".join(terms))

    if re.search(r"\badv\b", user_query, re.IGNORECASE) and re.search(r"pixel", user_query, re.IGNORECASE):
        _add("advertising pixel Adobe Tags extension implementation")

    return queries


def build_clarification(
    retriever,
    user_query: str,
    search_query: str,
    *,
    product_intent: str | None,
    blocked_reason: str,
    refinement: RefinementResult | None,
    related_docs: list[dict] | None,
    max_options: int = _MAX_OPTIONS,
) -> ClarificationResult | None:
    """
    Build clarification options from near-neighbor docs when retrieval is blocked.

    Returns None when no viable neighbors exist (caller should fall back to hard block).
    """
    probe_pools: list[list[dict]] = []
    for q in _expanded_search_queries(user_query, search_query):
        probe_pools.append(_probe_neighbors(retriever, user_query, q))
    unfiltered = _merge_docs(probe_pools)
    gap_reasons = list(refinement.gap_reasons) if refinement else []

    # Prefer unfiltered neighbors when product filter hid stronger matches.
    if "product_filter_excluded_stronger_neighbors" in gap_reasons:
        pool = unfiltered
    else:
        pool = _merge_docs([unfiltered, related_docs or []])

    terms = _expand_query_terms(user_query)
    ranked = _rank_neighbors_for_refinement(user_query, terms, pool)
    ranked = _dedupe_neighbor_docs(ranked)

    options: list[ClarificationOption] = []
    seen_titles: set[str] = set()

    for doc in ranked:
        if len(options) >= max_options:
            break
        score = float(doc.get("score", 0))
        if score < _MIN_NEIGHBOR_SCORE:
            continue

        meta = doc.get("metadata") or {}
        title = _clean_title(meta.get("title", ""))
        if not title:
            continue

        title_key = title.lower()
        if title_key in seen_titles:
            continue
        seen_titles.add(title_key)

        product = meta.get("product") or product_intent or ""
        preview_url = _doc_preview_url(doc)
        s3_key = meta.get("s3_key") or ""

        opt_id = f"opt-{len(options) + 1}"
        sim_score, strength = _match_strength(score)
        options.append(
            ClarificationOption(
                id=opt_id,
                label=_option_label(title, product),
                query=_option_query(title, product),
                product=product,
                doc_title=title,
                preview_url=preview_url,
                doc_anchor_s3_key=s3_key,
                similarity_score=sim_score,
                match_strength=strength,
            )
        )

    if not options:
        return None

    return ClarificationResult(
        genesis=_build_genesis(user_query, product_intent),
        options=options,
        original_query=user_query,
        blocked_reason=blocked_reason,
        intent_summary="",
    )


def clarification_selection_to_routing(selection: dict[str, Any]) -> dict[str, Any]:
    """Normalise API clarification payload for the retrieval path."""
    return {
        "product_override": selection.get("product_override") or selection.get("product"),
        "resolved_query": selection.get("resolved_query") or selection.get("query", ""),
        "doc_anchor_s3_key": selection.get("doc_anchor_s3_key") or "",
        "skip_topical_gate": True,
        "option_id": selection.get("option_id", ""),
        "original_query": selection.get("original_query", ""),
    }
