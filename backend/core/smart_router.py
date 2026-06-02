"""
Smart model router — selects Haiku or Sonnet based on query complexity.

Haiku  → simple definitions, "what is", short lookups, reference questions
Sonnet → how-to procedures, creation tasks, comparisons, troubleshooting,
         multi-step workflows, schema/segment/connection creation
"""

import re

# ── Sonnet triggers ────────────────────────────────────────────────────────────
# Procedural / creation verbs
_CREATION_VERBS = re.compile(
    r'\b(create|build|set up|setup|configure|implement|migrate|integrate|'
    r'design|develop|deploy|install|enable|connect|map|transform|ingest|'
    r'calculate|define metric|define segment|add|remove|delete|update|edit)\b',
    re.IGNORECASE,
)

# Technical complexity keywords
_COMPLEX_KEYWORDS = re.compile(
    r'\b(segment|filter|calculated metric|derived field|attribution|'
    r'schema|xdm|dataset|connection|data view|report suite|evar|prop|'
    r'marketing channel|classification|processing rule|data feed|'
    r'identity|profile|audience|destination|source|sandbox|'
    r'troubleshoot|debug|error|issue|not working|broken|'
    r'difference between|compare|vs\.|versus|migrate|upgrade|'
    r'step[- ]by[- ]step|how do i|how to|can i|workflow|process)\b',
    re.IGNORECASE,
)

# Simple definition patterns → Haiku (only if no creation verb + short)
_DEFINITION_PATTERNS = re.compile(
    r'^(what is|what are|what does|define|explain|describe|tell me about|'
    r'what does .+ mean)',
    re.IGNORECASE,
)

# Comparison / mechanism patterns → always Sonnet regardless of length
_SONNET_OVERRIDE = re.compile(
    r'\b(difference between|compare|vs\.?|versus|how does .+ work|'
    r'when should i|which is better|pros and cons|trade.?off)\b',
    re.IGNORECASE,
)


def classify_query(query: str) -> str:
    """
    Returns 'haiku' or 'sonnet'.

    Logic:
      1. Short simple definition questions → haiku
      2. Creation verbs or complex keywords → sonnet
      3. Long queries (>12 words) with question structure → sonnet
      4. Default → haiku (fast and cheap for lookups)
    """
    q = query.strip()
    word_count = len(q.split())

    is_definition = bool(_DEFINITION_PATTERNS.match(q))
    has_creation = bool(_CREATION_VERBS.search(q))
    has_complexity = bool(_COMPLEX_KEYWORDS.search(q))
    has_override = bool(_SONNET_OVERRIDE.search(q))

    # Comparisons, mechanism questions → always Sonnet
    if has_override:
        return "sonnet"

    # Simple definition of ANY topic (even complex ones) → Haiku
    # e.g. "What is a segment?" stays Haiku; "How do I create a segment?" goes Sonnet
    if is_definition and not has_creation and word_count <= 12:
        return "haiku"

    # Explicit procedural / creation intent → always Sonnet
    if has_creation:
        return "sonnet"

    # Complex topic + not a simple definition → Sonnet
    if has_complexity and not is_definition:
        return "sonnet"

    # Long multi-part questions → Sonnet
    if word_count > 12:
        return "sonnet"

    # Short queries with no signals → Haiku
    return "haiku"
