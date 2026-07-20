"""
Topical relevance — gate retrieval results before LLM synthesis.

Ensures query terms (especially topic keywords) appear in doc title, URL path,
or snippet before a chunk is used for answers or shown as a source.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from backend.core.query_keywords import extract_terms
from backend.core.retrieval_refiner import _lexical_overlap

_TITLE_CLEAN_RE = re.compile(r"\s*\{#[^}]+\}")

# Product / vendor terms — too broad to require as topical matches.
_GENERIC_TERMS = frozenset({
    "adobe", "experience", "platform", "analytics", "customer", "journey",
    "optimizer", "target", "collection", "data", "cloud", "real", "time",
    "aep", "ajo", "cja", "aa", "rtcdp", "exl", "docs", "documentation",
    "different", "various", "types", "what", "are", "the", "for", "about",
    # Procedural/creation verbs — near-universal across how-to docs, so
    # requiring a URL/title match on these (rather than the real topic
    # nouns) causes multi-step workflow queries to match the wrong doc
    # or drop the right ones.
    "steps", "step", "process", "full", "creating", "create", "created",
    "building", "build", "built", "setting", "set", "setup", "configuring",
    "configure", "implementing", "implement", "activating", "activate",
    "connecting", "connect", "integrating", "integrate", "using", "use",
    "then",
})

# Minimum topical score for a doc to be used for answers / sources.
TOPICAL_THRESHOLD = 0.20

# When the query has 2+ significant terms, require at least one in URL path or title.
_MIN_SIGNIFICANT_FOR_URL_CHECK = 2


def significant_terms(query: str) -> list[str]:
    """Topic terms from the user query, excluding generic product vocabulary."""
    from backend.core.query_keywords import extract_query_keywords

    kw = extract_query_keywords(query)
    terms = kw.match_terms[:10] if kw.match_terms else extract_terms(query)
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
    from backend.core.query_keywords import extract_query_keywords

    kw = extract_query_keywords(query)
    sig = significant_terms(query)
    terms = sig if sig else extract_terms(query)
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

    for phrase in kw.topic_phrases:
        pl = phrase.lower()
        if pl in text or pl.replace(" ", "-") in url_path:
            score = min(1.0, score + 0.12)
            break

    return min(1.0, score)


_STEM_SUFFIXES = ("ing", "ers", "er", "es", "ed", "s")
_WORD_RE = re.compile(r"[a-z0-9]+")


def _stem(word: str) -> str:
    """
    Minimal suffix-stripping stemmer — just enough to match word-form variants
    like "testing"/"test" or "activities"/"activity" without pulling in a full
    NLP stemmer for what's a narrow, low-risk normalization. Only strips when
    the remainder is still >=3 chars, so short words ("as", "is") are untouched.
    """
    lower = word.lower()
    # "-ies" plural (activity/activities, identity/identities) needs its own
    # rule before the generic suffix loop below — stripping "es" alone would
    # leave "activiti", not "activity"; the "y" must be restored.
    if lower.endswith("ies") and len(lower) - 3 >= 3:
        return lower[:-3] + "y"
    for suf in _STEM_SUFFIXES:
        if lower.endswith(suf) and len(lower) - len(suf) >= 3:
            return lower[: -len(suf)]
    return lower


def has_direct_url_match(query: str, doc: dict) -> bool:
    """
    True when at least one significant query term appears in the doc URL path
    or title, tolerating word-form variants (stem match, not exact substring).

    Falls back to repo_path/s3_key when url metadata is empty — same fallback
    doc_relevance_text() already uses for topical_match_score(), so a doc
    isn't penalized on this check alone just for missing a `url` field while
    still scoring well on the snippet-based topical score.
    """
    sig = significant_terms(query)
    if len(sig) < 1:
        return True

    meta = doc.get("metadata") or {}
    title = _clean_title(meta.get("title", "")).lower()
    url_field = meta.get("url") or meta.get("repo_path") or meta.get("s3_key") or ""
    url_path = _url_path_text(url_field)

    haystack_words = {_stem(w) for w in _WORD_RE.findall(title)} | {
        _stem(w) for w in _WORD_RE.findall(url_path)
    }

    for term in sig:
        term_words = _WORD_RE.findall(term.lower())
        if not term_words:
            continue
        # Multi-word terms (e.g. "AJO journey") require every constituent word
        # to have a stem match somewhere in the haystack — looser than the old
        # exact-contiguous-phrase substring check, but still requires the full
        # concept, not just one word of it, to be present.
        if all(_stem(w) in haystack_words for w in term_words):
            return True
    return False


def is_topically_relevant(
    query: str,
    doc: dict,
    *,
    threshold: float = TOPICAL_THRESHOLD,
) -> bool:
    """
    A doc that clears the base topical score already has enough term/URL/lex
    overlap to count as relevant. has_direct_url_match() is no longer a second
    rejection gate on top of that — a doc whose title/URL happens to be generic
    (e.g. "Audience evaluation methods" for a "batch/streaming/edge" query) was
    being dropped here despite a comfortably passing topical_match_score. Kept
    available for callers that want it as a signal (e.g. future ranking/logging),
    not as a pass/fail check.
    """
    return topical_match_score(query, doc) >= threshold


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

    When product_filter is set and fewer than _MIN_SIGNIFICANT_FOR_URL_CHECK
    significant terms survive (after stripping product names/action verbs),
    there's nothing meaningful left to lexically gate on — e.g. "step" is the
    sole survivor of "I'm new to CJA, how do I set it up step by step". Trust
    the product scope (a real Chroma where-clause) plus the embedding rank
    instead of rejecting every candidate on that one leftover term. With 2+
    real significant terms, keep full gating — that's what filters out a
    same-product-but-wrong-subtopic doc (e.g. an AEP accessibility page
    surfacing for an "ingestion guardrails" query).
    """
    product_docs = filter_by_product(docs, product_filter)
    pool = product_docs if product_filter else docs
    if product_filter and len(significant_terms(query)) < _MIN_SIGNIFICANT_FOR_URL_CHECK:
        relevant_docs = sorted(pool, key=lambda d: float(d.get("score", 0.0)), reverse=True)
    else:
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
