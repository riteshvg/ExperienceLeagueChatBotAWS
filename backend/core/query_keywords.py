"""
Structured keyword extraction and hybrid retrieval support.

Extracts topic phrases (e.g. "Trade Desk scripts", "ADV pixels"), expands
Adobe/vendor synonyms, and builds embedding + document-contains search passes
to complement pure vector retrieval.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_STOPWORDS = frozenset({
    "what", "how", "does", "the", "and", "for", "with", "via", "from", "that",
    "this", "are", "can", "you", "your", "about", "when", "where", "which",
    "into", "using", "use", "set", "get", "have", "has", "was", "were", "will",
    "should", "would", "could", "their", "they", "them", "then", "than", "also",
    "just", "only", "not", "but", "all", "any", "our", "its", "a", "an", "to",
    "of", "in", "on", "at", "by", "or", "as", "be", "do", "i", "me", "my", "we",
})
_CAMEL_RE = re.compile(r"[a-z]+(?:[A-Z][a-z0-9]*)+")
_SHORT_ALLOW = frozenset({"sdk", "web", "aep", "ajo", "cja", "api", "xdm", "adv"})


def extract_terms(query: str) -> list[str]:
    """Tokenize a query into searchable terms (shared with retrieval refiner)."""
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

# Shared acronym / informal → documentation vocabulary.
TERM_SYNONYMS: dict[str, list[str]] = {
    "adv": ["advertising", "advertising pixel"],
    "pixel": ["pixel"],
    "pixels": ["pixel"],
    "launch": ["adobe tags", "tags"],
    "dtm": ["dynamic tag management", "tags"],
    "trade": ["trade desk"],
    "desk": ["trade desk"],
    "meta": ["meta pixel"],
    "facebook": ["meta pixel"],
}

# Multi-word phrases detected in queries (lowercase key → search variants).
PHRASE_SYNONYMS: dict[str, list[str]] = {
    "trade desk": ["trade desk", "the trade desk"],
    "adv pixels": ["advertising pixel", "advertising pixels", "meta pixel"],
    "adv pixel": ["advertising pixel", "meta pixel"],
    "meta pixel": ["meta pixel extension"],
}

_ACTION_TERMS = frozenset({
    "implement", "install", "configure", "setup", "set", "create", "use",
    "enable", "add", "deploy", "inside", "within", "using", "how", "walk",
})

_GENERIC_TERMS = frozenset({
    "adobe", "experience", "platform", "analytics", "customer", "journey",
    "optimizer", "target", "collection", "data", "cloud", "real", "time",
    "aep", "ajo", "cja", "aa", "rtcdp", "exl", "docs", "documentation",
    "the", "and", "for", "with", "from", "into", "about",
})

_PHRASE_CAP_RE = re.compile(
    r"\b(?:The\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b",
)
_ACRONYM_PHRASE_RE = re.compile(r"\b([A-Z]{2,})\s+([a-z]{3,}s?)\b")
_QUOTED_RE = re.compile(r'["\']([^"\']+)["\']')

# Common documentation nouns that carry no topical signal on their own — pairing
# one of these with a bare product acronym (e.g. "AEP request", "CJA data") produces
# an embedding probe that matches almost any doc dominated by the product's own name,
# drowning out genuinely on-topic results. See _has_generic_acronym_pairing().
_GENERIC_ACRONYM_PAIR_NOUNS = frozenset({
    "request", "requests", "call", "calls", "data", "event", "events",
    "response", "responses", "issue", "issues", "problem", "problems",
    "error", "errors", "report", "reports", "call/dispatch",
})


def _has_generic_acronym_pairing(phrase: str) -> bool:
    """True when phrase is a bare acronym + a generic noun (e.g. "AEP request")."""
    match = _ACRONYM_PHRASE_RE.fullmatch(phrase.strip())
    if not match:
        return False
    return match.group(2).lower() in _GENERIC_ACRONYM_PAIR_NOUNS


@dataclass
class QueryKeywords:
    raw_query: str
    topic_phrases: list[str] = field(default_factory=list)
    product_phrases: list[str] = field(default_factory=list)
    match_terms: list[str] = field(default_factory=list)
    embedding_queries: list[str] = field(default_factory=list)
    contains_phrases: list[str] = field(default_factory=list)


def _dedupe(items: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        key = item.lower().strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item.strip())
    return out


def _extract_topic_phrases(query: str) -> list[str]:
    phrases: list[str] = []

    for m in _QUOTED_RE.finditer(query):
        phrases.append(m.group(1).strip())

    for m in _PHRASE_CAP_RE.finditer(query):
        phrases.append(m.group(1).strip())

    for m in _ACRONYM_PHRASE_RE.finditer(query):
        phrases.append(f"{m.group(1)} {m.group(2)}")

    # Consecutive significant tokens: "trade desk scripts" from lower query
    lower = query.lower()
    for key in PHRASE_SYNONYMS:
        if key in lower:
            phrases.append(key)

    return _dedupe(phrases)


def _expand_term(term: str) -> list[str]:
    lower = term.lower()
    expanded = [term]
    for syn in TERM_SYNONYMS.get(lower, []):
        expanded.append(syn)
    return expanded


def _expand_phrase(phrase: str) -> list[str]:
    lower = phrase.lower()
    variants = [phrase]
    for syn in PHRASE_SYNONYMS.get(lower, []):
        variants.append(syn)
    # Also expand embedded acronyms
    for token in lower.split():
        variants.extend(TERM_SYNONYMS.get(token, []))
    return _dedupe(variants)


def extract_query_keywords(query: str, product_intent: str | None = None) -> QueryKeywords:
    """Extract phrases, match terms, and retrieval queries from a user question."""
    topic_phrases = _extract_topic_phrases(query)
    base_terms = extract_terms(query)

    match_terms: list[str] = []
    for term in base_terms:
        if term.lower() in _GENERIC_TERMS or term.lower() in _ACTION_TERMS:
            continue
        match_terms.extend(_expand_term(term))

    for phrase in topic_phrases:
        for part in phrase.split():
            if part.lower() not in _GENERIC_TERMS and part.lower() not in _ACTION_TERMS:
                match_terms.extend(_expand_term(part))
        match_terms.extend(_expand_phrase(phrase))

    if product_intent:
        product_phrases = [product_intent]
        # Short label for matching (e.g. "Data Collection")
        short = product_intent.replace("Adobe ", "")
        if short.lower() not in product_intent.lower():
            product_phrases.append(short)
    else:
        product_phrases = []

    match_terms = _dedupe(match_terms)

    # Focused embedding queries — phrase + product context + synonyms.
    embedding_queries: list[str] = [query.strip()]
    for phrase in topic_phrases[:3]:
        expanded = _expand_phrase(phrase)
        embedding_queries.append(expanded[0])
        # Skip "{acronym} {generic noun} {product name}" — e.g. "AEP request Adobe
        # Experience Platform" — it carries no topical signal beyond the product's
        # own name and out-ranks genuinely relevant docs in the hybrid merge.
        if product_intent and not _has_generic_acronym_pairing(phrase):
            embedding_queries.append(f"{expanded[0]} {product_intent}")
        if len(expanded) > 1:
            embedding_queries.append(f"{expanded[0]} {expanded[1]} Adobe Tags implementation")

    # Single-token synonym probes for acronyms in the query.
    for term in base_terms:
        for syn in TERM_SYNONYMS.get(term.lower(), [])[:2]:
            q = f"{syn} Adobe Tags extension implementation"
            embedding_queries.append(q)

    contains_phrases: list[str] = []
    for phrase in topic_phrases:
        contains_phrases.extend(_expand_phrase(phrase))
    for term in match_terms[:6]:
        if len(term) >= 4:
            contains_phrases.append(term)

    return QueryKeywords(
        raw_query=query,
        topic_phrases=topic_phrases,
        product_phrases=product_phrases,
        match_terms=match_terms,
        embedding_queries=_dedupe(embedding_queries)[:6],
        contains_phrases=_dedupe(contains_phrases)[:5],
    )


def keyword_match_score(keywords: QueryKeywords, doc: dict) -> float:
    """
    Score 0–1 for how well doc title/URL/snippet matches extracted keywords.
    Phrase hits weigh more than single-token hits.
    """
    from backend.core.topical_relevance import doc_relevance_text

    if not keywords.match_terms and not keywords.topic_phrases:
        return 0.0

    text = doc_relevance_text(doc)
    meta = doc.get("metadata") or {}
    title = (meta.get("title") or "").lower()
    url = (meta.get("url") or meta.get("s3_key") or "").lower()

    phrase_hits = 0
    for phrase in keywords.topic_phrases:
        pl = phrase.lower()
        if pl in text or pl.replace(" ", "-") in url:
            phrase_hits += 1
        for variant in _expand_phrase(phrase):
            if variant.lower() in text or variant.lower() in title:
                phrase_hits += 1
                break

    term_hits = sum(1 for t in keywords.match_terms if t.lower() in text)

    phrase_total = max(len(keywords.topic_phrases), 1)
    term_total = max(len(keywords.match_terms), 1)
    score = (phrase_hits / phrase_total) * 0.55 + (term_hits / term_total) * 0.45
    return min(1.0, score)


def hybrid_doc_score(
    doc: dict,
    keywords: QueryKeywords,
    user_query: str,
    *,
    embed_weight: float = 0.45,
) -> float:
    """Blend embedding similarity with keyword alignment."""
    embed = float(doc.get("score", 0.0))
    kw = keyword_match_score(keywords, doc)
    if embed < 0.15:
        embed_weight = 0.25
    return embed * embed_weight + kw * (1.0 - embed_weight)
