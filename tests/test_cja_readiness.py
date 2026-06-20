"""Tests for CJA readiness evaluation (mocked retriever)."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from backend.core.cja_readiness import evaluate_cja_question, MIN_CJA_CHUNKS


def _doc(title: str, product: str = "Customer Journey Analytics", score: float = 0.45):
    return {
        "content": f"Documentation about {title}.",
        "score": score,
        "metadata": {
            "title": title,
            "product": product,
            "url": f"https://experienceleague.adobe.com/en/docs/analytics-platform/using/cja-workspace/{title.lower().replace(' ', '-')}",
            "s3_key": f"adobe-docs/customer-journey-analytics/help/components/{title.lower().replace(' ', '-')}.md",
        },
    }


class TestCjaReadiness:
    def test_direct_question_passes_with_relevant_docs(self):
        retriever = MagicMock()
        settings = SimpleNamespace(max_retrieval_results=8, similarity_threshold=0.3)

        docs = [_doc("Introduction to Customer Journey Analytics", score=0.55)]
        with patch("backend.core.cja_readiness.retrieve_with_refinement", return_value=(docs, None)):
            result = evaluate_cja_question(
                retriever,
                settings,
                question_id="cja-overview",
                query="What is Customer Journey Analytics?",
                expect="direct",
                min_topical=0.20,
            )
        assert result.passed
        assert result.outcome == "direct"

    def test_clarify_acceptable_when_neighbors_exist(self):
        retriever = MagicMock()
        settings = SimpleNamespace(max_retrieval_results=8, similarity_threshold=0.3)

        docs = [_doc("Configure a datastream", product="Adobe Data Collection", score=0.35)]
        with patch("backend.core.cja_readiness.retrieve_with_refinement", return_value=(docs, None)):
            with patch("backend.core.cja_readiness.assess_retrieval") as assess:
                assess.return_value = {"relevant_docs": [], "product_docs": docs}
                result = evaluate_cja_question(
                    retriever,
                    settings,
                    question_id="calc-vs-derived",
                    query="What is the difference between calculated metrics and derived fields in CJA?",
                    expect="direct_or_clarify",
                    min_topical=0.15,
                )
        assert result.passed
        assert result.outcome in {"no_direct_match", "weak_topical", "direct"}

    def test_corpus_threshold_constant(self):
        assert MIN_CJA_CHUNKS >= 4000
