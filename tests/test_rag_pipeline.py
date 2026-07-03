"""Tests for RAGPipeline._run_retrieval_path's weak-topical-alignment gate.

backend/core/rag_pipeline.py has its own 'best_topical < 0.22' check, separate
from (and downstream of) topical_relevance.assess_retrieval's per-doc gate.
It exists to avoid answering confidently when retrieved docs only superficially
resemble the query — but it independently re-applies topical_match_score, so it
can undo assess_retrieval's product-scoped thin-significant-terms bypass unless
it's relaxed under the same condition.
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from backend.core.rag_pipeline import RAGPipeline

SETTINGS = SimpleNamespace(max_retrieval_results=15, similarity_threshold=0.2)


def _doc(title: str, score: float = 0.7) -> dict:
    return {
        "content": f"Documentation about {title}.",
        "score": score,
        "metadata": {"title": title, "product": "Customer Journey Analytics"},
    }


def _run_retrieval_path(query, product_intent, sig_terms, best_topical):
    docs = [
        _doc("Introduction to Customer Journey Analytics"),
        _doc("Understanding Customer Journey Analytics"),
    ]
    pipeline = RAGPipeline(retriever=MagicMock(), session_store=MagicMock())
    with (
        patch("backend.core.rag_pipeline.retrieve_with_refinement", return_value=(docs, None)),
        patch(
            "backend.core.rag_pipeline.assess_retrieval",
            return_value={"relevant_docs": docs, "product_docs": docs, "topical_scores": {}},
        ),
        patch("backend.core.rag_pipeline.significant_terms", return_value=sig_terms),
        patch("backend.core.rag_pipeline.topical_match_score", return_value=best_topical),
    ):
        return asyncio.run(
            pipeline._run_retrieval_path(
                query=query,
                search_query=query,
                settings=SETTINGS,
                product_intent=product_intent,
                where_filter=None,
            )
        )


class TestWeakTopicalAlignmentGate:
    def test_thin_terms_with_product_scope_bypasses_gate(self):
        """Broad query where 'step' is the only significant term, product
        correctly scoped — weak topical alignment no longer forces a refusal."""
        relevant_docs, _, _, _, blocked = _run_retrieval_path(
            query="how do i setup cja step by step",
            product_intent="Customer Journey Analytics",
            sig_terms=["step"],
            best_topical=0.0,
        )
        assert blocked is None
        assert relevant_docs

    def test_real_significant_terms_still_gated(self):
        """2+ real significant terms — protection against docs that only
        superficially resemble the query is preserved even with product_intent set."""
        _, _, _, _, blocked = _run_retrieval_path(
            query="What are the different ingestion guardrails for Customer Journey Analytics?",
            product_intent="Customer Journey Analytics",
            sig_terms=["ingestion", "guardrails"],
            best_topical=0.0,
        )
        assert blocked == "no_direct_match"

    def test_thin_terms_without_product_scope_still_gated(self):
        """Thin significant terms alone isn't enough to bypass — the relaxation
        only applies once retrieval was actually hard-scoped to a product."""
        _, _, _, _, blocked = _run_retrieval_path(
            query="how do i set it up step by step",
            product_intent=None,
            sig_terms=["step"],
            best_topical=0.0,
        )
        assert blocked == "no_direct_match"
