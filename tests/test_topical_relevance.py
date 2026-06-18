"""Tests for topical relevance gating and evidence scoring."""

from backend.core.evidence import build_evidence
from backend.core.topical_relevance import (
    assess_retrieval,
    filter_relevant_docs,
    has_direct_url_match,
    is_topically_relevant,
    topical_match_score,
)


def _doc(title: str, url: str, product: str, content: str = "", score: float = 0.5):
    return {
        "content": content,
        "score": score,
        "metadata": {
            "title": title,
            "url": url,
            "product": product,
            "repo_path": f"help/{title.lower().replace(' ', '-')}.md",
            "s3_key": f"adobe-docs/experience-platform/help/{title.lower().replace(' ', '-')}.md",
        },
    }


QUERY = "What are the different ingestion guardrails for Adobe Experience Platform?"


class TestTopicalRelevance:
    def test_accessibility_not_relevant_to_guardrails(self):
        doc = _doc(
            "General Accessibility Features in Experience Platform",
            "https://experienceleague.adobe.com/en/docs/experience-platform/accessibility/features",
            "Adobe Experience Platform",
            "Users with disabilities frequently rely on assistive technologies.",
            score=0.468,
        )
        assert not is_topically_relevant(QUERY, doc)
        assert not has_direct_url_match(QUERY, doc)

    def test_ingestion_guardrails_doc_is_relevant(self):
        doc = _doc(
            "Guardrails for Data Ingestion",
            "https://experienceleague.adobe.com/en/docs/experience-platform/ingestion/guardrails",
            "Adobe Experience Platform",
            "Guardrails are thresholds that provide guidance for data ingestion.",
            score=0.62,
        )
        assert is_topically_relevant(QUERY, doc)
        assert has_direct_url_match(QUERY, doc)
        assert topical_match_score(QUERY, doc) >= 0.20

    def test_ajo_ingestion_snippet_without_url_match_fails_multi_term_check(self):
        doc = _doc(
            "Journey Optimizer Get Started for Data Engineer",
            "",
            "Adobe Journey Optimizer",
            "Configure source connectors. Adobe Journey Optimizer allows data to be ingested from external sources.",
            score=0.71,
        )
        assert not is_topically_relevant(QUERY, doc)

    def test_filter_relevant_docs_excludes_accessibility(self):
        docs = [
            _doc(
                "General Accessibility Features in Experience Platform",
                "https://experienceleague.adobe.com/en/docs/experience-platform/accessibility/features",
                "Adobe Experience Platform",
                score=0.468,
            ),
            _doc(
                "Guardrails for Data Ingestion",
                "https://experienceleague.adobe.com/en/docs/experience-platform/ingestion/guardrails",
                "Adobe Experience Platform",
                "Batch and streaming ingestion guardrails.",
                score=0.55,
            ),
        ]
        relevant = filter_relevant_docs(QUERY, docs)
        assert len(relevant) == 1
        assert "Guardrails" in relevant[0]["metadata"]["title"]

    def test_assess_retrieval_with_product_filter(self):
        docs = [
            _doc("Leverage context data", "", "Adobe Journey Optimizer", "ingestion context", 0.71),
            _doc(
                "General Accessibility Features in Experience Platform",
                "https://experienceleague.adobe.com/en/docs/experience-platform/accessibility/features",
                "Adobe Experience Platform",
                score=0.468,
            ),
        ]
        result = assess_retrieval(QUERY, docs, "Adobe Experience Platform")
        assert len(result["product_docs"]) == 1
        assert len(result["relevant_docs"]) == 0


class TestEvidenceScoring:
    def test_evidence_scores_from_displayable_sources_not_hidden_high_scores(self):
        """High-similarity docs without URLs must not inflate evidence level."""
        docs = [
            _doc("Leverage context data", "", "Adobe Journey Optimizer", score=0.712),
            _doc(
                "General Accessibility Features in Experience Platform",
                "https://experienceleague.adobe.com/en/docs/experience-platform/accessibility/features",
                "Adobe Experience Platform",
                score=0.468,
            ),
        ]
        evidence = build_evidence(docs)
        assert evidence["top_score"] == 0.468
        assert evidence["evidence_level"] == "moderate"
        assert evidence["source_count"] == 1

    def test_no_direct_match_forces_weak_evidence(self):
        related = [
            _doc(
                "General Accessibility Features in Experience Platform",
                "https://experienceleague.adobe.com/en/docs/experience-platform/accessibility/features",
                "Adobe Experience Platform",
                score=0.755,
            ),
        ]
        evidence = build_evidence([], failure_reason="no_direct_match", related_docs=related, topical_scores={
            related[0]["metadata"]["s3_key"]: 0.0,
        })
        assert evidence["evidence_level"] == "weak"
        assert evidence["grounding_level"] == "insufficient"
        assert evidence["citation_count"] == 0
        assert evidence["sources"][0]["score"] == 0.0
        assert all(not s.get("cited") for s in evidence["sources"])

    def test_no_direct_match_banner(self):
        evidence = build_evidence([], failure_reason="no_direct_match")
        assert "No directly matching documentation" in evidence["banner"]
        assert evidence["evidence_level"] == "none"

    def test_refinement_banner_suppressed_on_no_direct_match(self):
        evidence = build_evidence(
            [],
            failure_reason="no_direct_match",
            refinement={"refinement_applied": True, "refinement_neighbors": ["Some neighbor"]},
        )
        assert "documentation-aligned search" not in (evidence["banner"] or "")
