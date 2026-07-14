"""
Three evaluators for the Rovr golden-set eval:

  a) correctness        — LLM-as-judge, key-facts-present, not phrasing match
  b) citation_accuracy  — deterministic URL comparison, no LLM
  c) product_scoping    — deterministic product comparison, no LLM

Each takes (run, example) per the langsmith.evaluate() row-level evaluator
signature and returns {"key": ..., "score": ..., "comment": ...}.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from config.settings import get_settings

EXPECTED_PRODUCT_MAP = {
    "AEP": "Adobe Experience Platform",
    "CJA": "Customer Journey Analytics",
    "Launch": "Adobe Data Collection",
    "AJO": "Adobe Journey Optimizer",
    "Adobe Analytics": "Adobe Analytics",
    "Target": "Adobe Target",
    "RT-CDP": "Adobe Experience Platform",
    None: None,
}


# ── (b) Citation accuracy — deterministic ────────────────────────────────────

def _normalize_url(url: str) -> str:
    """Strip trailing slash, fragment, and query string; lowercase scheme/host."""
    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower()
    netloc = parts.netloc.lower()
    path = parts.path.rstrip("/")
    return urlunsplit((scheme, netloc, path, "", ""))


def citation_accuracy(run, example) -> dict:
    expected_raw = (example.outputs or {}).get("expected_citation_urls") or []
    if isinstance(expected_raw, str):
        expected_raw = [expected_raw] if expected_raw else []
    expected = {_normalize_url(u) for u in expected_raw}

    actual_raw = (run.outputs or {}).get("citations") or []
    actual = {_normalize_url(u) for u in actual_raw}

    if not expected:
        # No specific URL was asserted for this entry (e.g. multi-product/
        # ambiguous queries with no single right answer) — nothing to check.
        return {
            "key": "citation_accuracy",
            "score": None,
            "comment": "No expected_citation_urls for this entry — skipped.",
        }

    hit = expected & actual
    score = len(hit) / len(expected)
    comment = (
        f"expected={sorted(expected)} actual={sorted(actual)} "
        f"matched={sorted(hit)} (score=hits/expected; `citations` already only "
        f"contains sources the pipeline marked cited=true — see "
        f"backend/core/evidence.py build_evidence(), cited = doc was part of "
        f"raw_docs injected into the LLM's prompt context)"
    )
    return {"key": "citation_accuracy", "score": score, "comment": comment}


# ── (c) Product scoping — deterministic ──────────────────────────────────────

def product_scoping(run, example) -> dict:
    expected_label = (example.outputs or {}).get("expected_product")
    expected = EXPECTED_PRODUCT_MAP.get(expected_label, expected_label)
    actual = (run.outputs or {}).get("detected_product")

    # None is a valid, correct result for intentionally multi-product/
    # ambiguous queries (expected_product is null in the golden set) — this
    # must be a deterministic equality check, not an LLM judgment call.
    score = 1.0 if actual == expected else 0.0
    comment = f"expected={expected!r} actual={actual!r}"
    return {"key": "product_scoping", "score": score, "comment": comment}


# ── (a) Correctness — LLM-as-judge ───────────────────────────────────────────

_JUDGE_MODEL = "claude-haiku-4-5-20251001"

_JUDGE_SYSTEM = """You are grading whether an AI assistant's answer covers the key facts \
of an expected answer summary for an Adobe Experience Cloud documentation question.

Score on FACT COVERAGE, not phrasing or style. The actual answer can be longer, \
shorter, differently organized, or use different words — none of that matters. \
What matters: does the actual answer state the same key facts/claims as the \
expected summary, without contradicting them?

Score as a number from 0.0 to 1.0:
- 1.0: all key facts from the expected summary are present and not contradicted
- 0.5: some key facts present, some missing or vague
- 0.0: key facts missing entirely, or the actual answer contradicts the expected summary

Respond with ONLY a JSON object, no other text: {"score": <float>, "reasoning": "<one sentence>"}"""

_JUDGE_USER_TEMPLATE = """QUESTION:
{query}

EXPECTED ANSWER SUMMARY (ground truth key facts):
{expected}

ACTUAL ANSWER (to grade):
{actual}"""


def _get_judge_client():
    import anthropic

    settings = get_settings()
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def correctness(run, example) -> dict:
    expected = (example.outputs or {}).get("expected_answer_summary", "")
    actual = (run.outputs or {}).get("answer", "")
    query = (example.inputs or {}).get("query", "")

    if not expected or expected == "PLACEHOLDER":
        return {
            "key": "correctness",
            "score": None,
            "comment": "No expected_answer_summary to grade against — skipped.",
        }

    if not actual.strip():
        return {"key": "correctness", "score": 0.0, "comment": "Empty actual answer."}

    client = _get_judge_client()
    message = client.messages.create(
        model=_JUDGE_MODEL,
        max_tokens=200,
        system=_JUDGE_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": _JUDGE_USER_TEMPLATE.format(
                    query=query, expected=expected, actual=actual
                ),
            }
        ],
    )
    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
    try:
        parsed = json.loads(raw)
        score = float(parsed["score"])
        reasoning = parsed.get("reasoning", "")
    except (json.JSONDecodeError, KeyError, ValueError, IndexError):
        # Judge didn't return clean JSON — surface the raw text rather than
        # silently guessing a score.
        match = re.search(r'"score"\s*:\s*([0-9.]+)', raw)
        score = float(match.group(1)) if match else None
        reasoning = f"Judge response was not clean JSON: {raw[:200]}"

    return {"key": "correctness", "score": score, "comment": reasoning}


EVALUATORS = [correctness, citation_accuracy, product_scoping]
