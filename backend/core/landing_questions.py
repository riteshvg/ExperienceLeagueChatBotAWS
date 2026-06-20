"""Classify logged user queries by Rovr solution for the landing page."""

from __future__ import annotations

import re
from dataclasses import dataclass

from backend.core.smart_router import detect_product_intent

# UI category labels shown on the landing page.
SOLUTION_ANALYTICS = "Analytics"
SOLUTION_CJA = "CJA"
SOLUTION_AEP = "AEP"
SOLUTION_TARGET = "Target"
SOLUTION_AJO = "AJO"
SOLUTION_DATA_COLLECTION = "Data Collection"
SOLUTION_CROSS = "Cross-Product"
SOLUTION_GENERAL = "General"

PRODUCT_TO_SOLUTION: dict[str, str] = {
    "Adobe Analytics": SOLUTION_ANALYTICS,
    "Customer Journey Analytics": SOLUTION_CJA,
    "Adobe Experience Platform": SOLUTION_AEP,
    "Adobe Target": SOLUTION_TARGET,
    "Adobe Journey Optimizer": SOLUTION_AJO,
    "Adobe Data Collection": SOLUTION_DATA_COLLECTION,
}

# Extended keyword map for multi-product detection (includes short tokens).
_SOLUTION_KEYWORDS: list[tuple[str, str]] = [
    ("adobe analytics", "Adobe Analytics"),
    ("analysis workspace", "Adobe Analytics"),
    ("report suite", "Adobe Analytics"),
    ("customer journey analytics", "Customer Journey Analytics"),
    (" cja ", "Customer Journey Analytics"),
    ("adobe experience platform", "Adobe Experience Platform"),
    (" aep ", "Adobe Experience Platform"),
    ("real-time cdp", "Adobe Experience Platform"),
    ("rtcdp", "Adobe Experience Platform"),
    ("adobe target", "Adobe Target"),
    ("journey optimizer", "Adobe Journey Optimizer"),
    (" ajo ", "Adobe Journey Optimizer"),
    ("adobe tags", "Adobe Data Collection"),
    ("launch", "Adobe Data Collection"),
    ("data collection", "Adobe Data Collection"),
    ("web sdk", "Adobe Data Collection"),
    ("edge network", "Adobe Data Collection"),
]

_SHORT_TOKENS: dict[str, str] = {
    "cja": "Customer Journey Analytics",
    "aep": "Adobe Experience Platform",
    "ajo": "Adobe Journey Optimizer",
}

# Topic hints when the query omits an explicit product name.
_TOPIC_HINTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bdata view\b|\bstitching\b|\bconnection(s)?\b.*\bcja\b", re.I), "Customer Journey Analytics"),
    (re.compile(r"\bevar(s)?\b|\bprop(s)?\b|\bprocessing rule(s)?\b|\bmarketing channel(s)?\b|\bclassification(s)?\b", re.I), "Adobe Analytics"),
    (re.compile(r"\bxdm\b|\bschema registry\b|\bdataset(s)?\b|\bidentity (service|graph)\b|\bsandbox(es)?\b|\bsegment definition\b", re.I), "Adobe Experience Platform"),
    (re.compile(r"\b(a/b|ab) test\b|\bmbox\b|\bexperience targeting\b|\brecommendation(s)?\b", re.I), "Adobe Target"),
    (re.compile(r"\bjourney\b|\bfrequency cap(ping)?\b|\bdecision management\b|\borchestrated campaign\b", re.I), "Adobe Journey Optimizer"),
    (re.compile(r"\bdatastream(s)?\b|\bweb sdk\b|\badobe tags\b|\bextension(s)?\b.*\brule(s)?\b|\bevent forwarding\b", re.I), "Adobe Data Collection"),
]

LANDING_SOLUTIONS: tuple[str, ...] = (
    SOLUTION_ANALYTICS,
    SOLUTION_CJA,
    SOLUTION_AEP,
    SOLUTION_TARGET,
    SOLUTION_AJO,
    SOLUTION_DATA_COLLECTION,
    SOLUTION_CROSS,
    SOLUTION_GENERAL,
)

MIN_QUERY_LENGTH = 15
MAX_PER_SOLUTION = 15
ALL_TAB_PER_SOLUTION = 4

_QUESTION_START = re.compile(
    r"^(how|what|why|when|where|can|does|is|are|explain|tell me|help me|show me)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class LandingQuestion:
    text: str
    solution: str
    times_asked: int

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "solution": self.solution,
            "times_asked": self.times_asked,
        }


def _matched_products(query: str) -> set[str]:
    q = f" {query.lower()} "
    found: set[str] = set()
    for keyword, product in _SOLUTION_KEYWORDS:
        if keyword in q:
            found.add(product)
    for token, product in _SHORT_TOKENS.items():
        if re.search(rf"\b{re.escape(token)}\b", query, re.IGNORECASE):
            found.add(product)
    if not found:
        single = detect_product_intent(query)
        if single:
            found.add(single)
    return found


def _topic_hint_product(query: str) -> str | None:
    matched: set[str] = set()
    for pattern, product in _TOPIC_HINTS:
        if pattern.search(query):
            matched.add(product)
    if len(matched) == 1:
        return next(iter(matched))
    return None


def _looks_like_question(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) < MIN_QUERY_LENGTH:
        return False
    if "?" in stripped:
        return True
    return bool(_QUESTION_START.match(stripped))


def classify_solution(query: str) -> str | None:
    """Return a landing-page solution label, or None if not suitable for display."""
    products = _matched_products(query)
    if len(products) >= 2:
        return SOLUTION_CROSS
    if len(products) == 1:
        return PRODUCT_TO_SOLUTION.get(next(iter(products)))

    hinted = _topic_hint_product(query)
    if hinted:
        return PRODUCT_TO_SOLUTION.get(hinted)

    if _looks_like_question(query):
        return SOLUTION_GENERAL
    return None


def group_landing_questions(rows: list[dict], *, per_solution: int = MAX_PER_SOLUTION) -> dict:
    """Build landing payload from aggregated query log rows."""
    by_solution: dict[str, list[dict]] = {s: [] for s in LANDING_SOLUTIONS}
    all_questions: list[dict] = []
    seen_norm: set[str] = set()

    for row in rows:
        text = (row.get("query_text") or "").strip()
        if len(text) < MIN_QUERY_LENGTH:
            continue
        norm = text.lower()
        if norm in seen_norm:
            continue

        solution = classify_solution(text)
        if not solution:
            continue

        seen_norm.add(norm)
        item = LandingQuestion(
            text=text,
            solution=solution,
            times_asked=int(row.get("times_asked") or 1),
        )
        bucket = by_solution.setdefault(solution, [])
        if len(bucket) >= per_solution:
            continue
        bucket.append(item.to_dict())
        all_questions.append(item.to_dict())

    return {
        "questions": all_questions,
        "by_solution": by_solution,
        "total": len(all_questions),
    }


# Curated starter prompts when PostgreSQL has no classified queries yet.
FALLBACK_BY_SOLUTION: dict[str, list[str]] = {
    SOLUTION_ANALYTICS: [
        "How do I create a segment in Adobe Analytics?",
        "What is the difference between eVars and props in Adobe Analytics?",
        "How do I set up processing rules in Adobe Analytics?",
    ],
    SOLUTION_CJA: [
        "What is a Data View in Customer Journey Analytics?",
        "How do I create a calculated metric in CJA?",
        "How does stitching work in Customer Journey Analytics?",
    ],
    SOLUTION_AEP: [
        "What are the different ways to ingest data into Adobe Experience Platform?",
        "How do I create an XDM schema in Adobe Experience Platform?",
        "How do I set up identity resolution in Adobe Experience Platform?",
    ],
    SOLUTION_TARGET: [
        "How do I create an A/B test in Adobe Target?",
        "How do I set up Experience Targeting activities in Adobe Target?",
        "How do I use Recommendations in Adobe Target?",
    ],
    SOLUTION_AJO: [
        "How do I create a journey in Adobe Journey Optimizer?",
        "What is decision management in Adobe Journey Optimizer?",
        "How do I set up frequency capping rules in Adobe Journey Optimizer?",
    ],
    SOLUTION_DATA_COLLECTION: [
        "How do I install the Adobe Experience Platform Web SDK?",
        "What is the difference between Adobe Tags and the Web SDK?",
        "How do I configure a datastream for Edge Network?",
    ],
    SOLUTION_CROSS: [
        "How do I connect an Adobe Analytics report suite to CJA?",
        "How do I use AEP audiences in Adobe Target for personalisation?",
        "What is the difference between Adobe Analytics and Real-Time CDP for audience building?",
    ],
    SOLUTION_GENERAL: [
        "How do I troubleshoot missing data in my reports?",
        "What is the best way to validate tracking before go-live?",
        "How do I set up a new implementation from scratch?",
    ],
}


def fallback_landing_payload(*, per_solution: int = MAX_PER_SOLUTION) -> dict:
    by_solution: dict[str, list[dict]] = {s: [] for s in LANDING_SOLUTIONS}
    all_questions: list[dict] = []
    for solution, prompts in FALLBACK_BY_SOLUTION.items():
        for text in prompts[:per_solution]:
            item = {"text": text, "solution": solution, "times_asked": 0}
            by_solution[solution].append(item)
            all_questions.append(item)
    return {
        "questions": all_questions,
        "by_solution": by_solution,
        "total": len(all_questions),
        "source": "fallback",
    }


def build_landing_payload(rows: list[dict], *, per_solution: int = MAX_PER_SOLUTION) -> dict:
    grouped = group_landing_questions(rows, per_solution=per_solution)
    if grouped["total"] == 0:
        payload = fallback_landing_payload(per_solution=per_solution)
    else:
        grouped["source"] = "postgres"
        payload = grouped
    payload["all_tab_per_solution"] = ALL_TAB_PER_SOLUTION
    payload["max_per_solution"] = per_solution
    return payload
