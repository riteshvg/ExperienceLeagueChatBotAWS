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


def _run_retrieval_path(query, product_intent, sig_terms, best_topical, doc_score=0.7):
    docs = [
        _doc("Introduction to Customer Journey Analytics", score=doc_score),
        _doc("Understanding Customer Journey Analytics", score=doc_score),
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
            doc_score=0.1,
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
            doc_score=0.1,
        )
        assert blocked == "no_direct_match"


def _api_doc(score: float) -> dict:
    """A real API-reference doc: terse content, low embedding similarity to
    conversational phrasing is expected for this class of doc."""
    return {
        "content": (
            "Learn how to authenticate calls to the Analytics 2.0 Reporting "
            "API using OAuth Server-to-Server credentials."
        ),
        "score": score,
        "metadata": {
            "title": "Analytics 2.0 API Authentication",
            "url": "https://experienceleague.adobe.com/docs/analytics-apis/2-0/guides/authenticate.html",
            "product": "Analytics APIs",
        },
    }


def _run_api_override(query, product_intent, docs):
    """Like _run_retrieval_path, but does NOT mock topical_match_score or
    significant_terms — this exercises the real scoring the " APIs" override
    in rag_pipeline._run_retrieval_path depends on."""
    pipeline = RAGPipeline(retriever=MagicMock(), session_store=MagicMock())
    with (
        patch("backend.core.rag_pipeline.retrieve_with_refinement", return_value=(docs, None)),
        patch(
            "backend.core.rag_pipeline.assess_retrieval",
            return_value={"relevant_docs": docs, "product_docs": docs, "topical_scores": {}},
        ),
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


class TestApiProductOffTopicOverride:
    """The " APIs"-suffix bypass in _is_off_topic/_run_retrieval_path used to
    blindly drop the off-topic threshold to 0.05 for any product_intent ending
    in " APIs" (rag_pipeline.py, formerly ~L761), regardless of whether the
    retrieved docs actually matched the query topic — the same shape as the
    fixed generic-title/URL override (topical_relevance.has_direct_url_match).
    It's now demoted to a scoring input: the bypass only fires when
    topical_match_score (with "api"/"apis" excluded as generic terms, and the
    URL-hit bonus scaled by url_ratio rather than flat) clears 0.30, which real
    off-topic queries that merely namedrop the API product name do not reach.
    """

    def test_genuine_direct_api_query_bypasses_off_topic_block(self):
        _, _, _, _, blocked = _run_api_override(
            query="How do I authenticate requests to the Analytics 2.0 API?",
            product_intent="Analytics APIs",
            docs=[_api_doc(score=0.1)],
        )
        assert blocked is None

    def test_off_topic_query_namedropping_api_product_stays_blocked(self):
        """Shares exactly one real (non-generic) term with the doc
        ("authenticate") but is otherwise unrelated — must not bypass just
        because it mentions "Analytics API"."""
        _, _, _, _, blocked = _run_api_override(
            query=(
                "How do I authenticate my identity at passport control, "
                "unrelated to Analytics API"
            ),
            product_intent="Analytics APIs",
            docs=[_api_doc(score=0.1)],
        )
        assert blocked == "off_topic"

    def test_non_api_product_off_topic_query_still_blocked(self):
        """Regression: removing the internal API-suffix threshold relaxation
        from _is_off_topic must not change behavior for non-"APIs" products."""
        docs = [{
            "content": "CJA overview content.",
            "score": 0.1,
            "metadata": {
                "title": "Introduction to Customer Journey Analytics",
                "url": "https://experienceleague.adobe.com/docs/cja/intro.html",
                "product": "Customer Journey Analytics",
            },
        }]
        _, _, _, _, blocked = _run_api_override(
            query="What is the best pizza recipe",
            product_intent="Customer Journey Analytics",
            docs=docs,
        )
        assert blocked is not None
