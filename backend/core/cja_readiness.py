"""
CJA corpus readiness checks — retrieval-only smoke tests (no LLM).

Used by GET /api/admin/readiness/cja and scripts/run_cja_readiness.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from backend.core.query_processor import QueryProcessor
from backend.core.retrieval_refiner import retrieve_with_refinement
from backend.core.smart_router import detect_product_intent
from backend.core.topical_relevance import assess_retrieval, topical_match_score

Expectation = Literal["direct", "direct_or_clarify"]

# Smoke bank — aligned with prod sign-off topics (Analysis Workspace, metrics, connections).
CJA_READINESS_QUESTIONS: list[dict[str, Any]] = [
    {
        "id": "cja-overview",
        "query": "What is Customer Journey Analytics?",
        "expect": "direct",
        "min_topical": 0.20,
    },
    {
        "id": "data-view",
        "query": "How do I create a data view in Customer Journey Analytics?",
        "expect": "direct_or_clarify",
        "min_topical": 0.18,
    },
    {
        "id": "calc-vs-derived",
        "query": "What is the difference between calculated metrics and derived fields in CJA?",
        "expect": "direct_or_clarify",
        "min_topical": 0.15,
    },
    {
        "id": "calc-metrics-aw",
        "query": "How do calculated metrics work in Customer Journey Analytics Analysis Workspace?",
        "expect": "direct_or_clarify",
        "min_topical": 0.15,
    },
    {
        "id": "connections",
        "query": "How do I set up a connection in Customer Journey Analytics?",
        "expect": "direct_or_clarify",
        "min_topical": 0.18,
    },
    {
        "id": "guided-analysis",
        "query": "What is guided analysis in Customer Journey Analytics?",
        "expect": "direct_or_clarify",
        "min_topical": 0.18,
    },
]

MIN_CJA_CHUNKS = 4000
MIN_CJA_PAGES = 700


@dataclass
class CjaQuestionResult:
    id: str
    query: str
    passed: bool
    outcome: str
    best_score: float
    best_topical: float
    top_title: str
    details: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "query": self.query,
            "passed": self.passed,
            "outcome": self.outcome,
            "best_score": round(self.best_score, 3),
            "best_topical": round(self.best_topical, 3),
            "top_title": self.top_title,
            "details": self.details,
        }


@dataclass
class CjaReadinessReport:
    passed: bool
    cja_chunks: int
    cja_pages: int
    corpus_ok: bool
    questions: list[CjaQuestionResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        q_pass = sum(1 for q in self.questions if q.passed)
        return {
            "passed": self.passed,
            "corpus": {
                "chunks": self.cja_chunks,
                "pages": self.cja_pages,
                "ok": self.corpus_ok,
                "min_chunks": MIN_CJA_CHUNKS,
                "min_pages": MIN_CJA_PAGES,
            },
            "questions": {
                "passed": q_pass,
                "total": len(self.questions),
                "items": [q.to_dict() for q in self.questions],
            },
        }


def _blocked_outcome(relevant: list, raw: list, best_topical: float) -> str:
    if not raw:
        return "no_retrieval"
    if not relevant:
        return "no_direct_match"
    if best_topical < 0.22:
        return "weak_topical"
    return "direct"


def evaluate_cja_question(
    retriever,
    settings,
    *,
    question_id: str,
    query: str,
    expect: Expectation,
    min_topical: float,
) -> CjaQuestionResult:
    qp = QueryProcessor()
    enhanced, _ = qp.preprocess_query(query)
    product_intent = detect_product_intent(query) or "Customer Journey Analytics"
    where_filter = {"product": {"$eq": product_intent}}

    raw_docs, _ = retrieve_with_refinement(
        retriever,
        enhanced,
        query,
        n_results=settings.max_retrieval_results,
        similarity_threshold=settings.similarity_threshold,
        product_filter=product_intent,
        where_filter=where_filter,
    )

    assessment = assess_retrieval(query, raw_docs, product_intent)
    relevant = assessment["relevant_docs"]
    best_score = max((float(d.get("score", 0)) for d in raw_docs), default=0.0)
    pool = relevant or raw_docs
    best_topical = max((topical_match_score(query, d) for d in pool), default=0.0)
    top_title = ""
    if pool:
        top_title = (pool[0].get("metadata") or {}).get("title", "")[:80]

    outcome = _blocked_outcome(relevant, raw_docs, best_topical)

    if outcome == "direct" and best_topical >= min_topical:
        passed = True
        details = "Retrieval passed topical gate"
    elif expect == "direct_or_clarify" and outcome in {"no_direct_match", "weak_topical"} and best_score >= 0.20:
        passed = True
        details = "Clarification path acceptable — neighbors exist"
    elif outcome == "direct" and best_topical < min_topical:
        passed = expect == "direct_or_clarify" and best_score >= 0.20
        details = f"Low topical ({best_topical:.2f})"
    else:
        passed = False
        details = f"Outcome={outcome}, topical={best_topical:.2f}, score={best_score:.2f}"

    return CjaQuestionResult(
        id=question_id,
        query=query,
        passed=passed,
        outcome=outcome,
        best_score=best_score,
        best_topical=best_topical,
        top_title=top_title,
        details=details,
    )


def evaluate_cja_readiness(retriever, settings) -> CjaReadinessReport:
    breakdown = retriever.product_breakdown()
    cja_row = next(
        (r for r in breakdown if r.get("product") == "Customer Journey Analytics"),
        {"chunks": 0, "pages": 0},
    )
    cja_chunks = int(cja_row.get("chunks", 0))
    cja_pages = int(cja_row.get("pages", 0))
    corpus_ok = cja_chunks >= MIN_CJA_CHUNKS and cja_pages >= MIN_CJA_PAGES

    questions: list[CjaQuestionResult] = []
    for spec in CJA_READINESS_QUESTIONS:
        questions.append(
            evaluate_cja_question(
                retriever,
                settings,
                question_id=spec["id"],
                query=spec["query"],
                expect=spec["expect"],
                min_topical=float(spec.get("min_topical", 0.18)),
            )
        )

    q_ok = all(q.passed for q in questions)
    return CjaReadinessReport(
        passed=corpus_ok and q_ok,
        cja_chunks=cja_chunks,
        cja_pages=cja_pages,
        corpus_ok=corpus_ok,
        questions=questions,
    )
