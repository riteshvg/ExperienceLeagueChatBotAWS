"""Tests for clarification resolver — blocked-query disambiguation."""

from backend.core.clarification_resolver import (
    ClarificationResult,
    build_clarification,
    clarification_selection_to_routing,
)
from backend.core.retrieval_refiner import RefinementResult


def _neighbor(title: str, product: str, score: float = 0.42, s3_key: str = ""):
    return {
        "content": f"Documentation about {title}.",
        "score": score,
        "metadata": {
            "title": title,
            "product": product,
            "url": f"https://experienceleague.adobe.com/en/docs/experience-platform/tags/{title.lower().replace(' ', '-')}",
            "s3_key": s3_key or f"adobe-docs/data-collection/help/tags/{title.lower().replace(' ', '-')}.md",
        },
    }


QUERY = "How to implement ADV pixels in Adobe Data Collection?"


class TestClarificationResolver:
    def test_builds_options_from_neighbors(self, monkeypatch):
        neighbors = [
            _neighbor("Meta Pixel Extension Overview", "Adobe Experience Platform", 0.45),
            _neighbor("Event Forwarding Guided Setup", "Adobe Data Collection", 0.38),
            _neighbor("Tags Overview", "Adobe Data Collection", 0.35),
        ]
        monkeypatch.setattr(
            "backend.core.clarification_resolver._probe_neighbors",
            lambda *_args, **_kwargs: neighbors,
        )

        refinement = RefinementResult(
            gap_reasons=["product_filter_excluded_stronger_neighbors"],
        )
        result = build_clarification(
            retriever=None,
            user_query=QUERY,
            search_query=QUERY,
            product_intent="Adobe Data Collection",
            blocked_reason="no_direct_match",
            refinement=refinement,
            related_docs=[],
        )

        assert isinstance(result, ClarificationResult)
        assert result.has_options
        assert len(result.options) >= 2
        assert any("Meta Pixel" in o.doc_title for o in result.options)
        assert "don't have specific documentation" in result.genesis.lower()
        assert "**adv pixels" in result.genesis.lower() or "**ADV pixels" in result.genesis
        assert "pick an option from the below" in result.genesis.lower()
        assert result.options[0].similarity_score > 0
        assert result.options[0].match_strength in {"Strong", "Moderate", "Low", "Weak"}
        assert result.options[0].query.startswith("How do I")

    def test_returns_none_without_viable_neighbors(self, monkeypatch):
        monkeypatch.setattr(
            "backend.core.clarification_resolver._probe_neighbors",
            lambda *_args, **_kwargs: [],
        )
        result = build_clarification(
            retriever=None,
            user_query=QUERY,
            search_query=QUERY,
            product_intent="Adobe Data Collection",
            blocked_reason="no_retrieval",
            refinement=None,
            related_docs=[],
        )
        assert result is None

    def test_deduplicates_by_title(self, monkeypatch):
        dup = _neighbor("Meta Pixel Extension Overview", "Adobe Experience Platform", 0.40)
        dup2 = _neighbor("Meta Pixel Extension Overview", "Adobe Experience Platform", 0.50)
        monkeypatch.setattr(
            "backend.core.clarification_resolver._probe_neighbors",
            lambda *_args, **_kwargs: [dup, dup2],
        )
        result = build_clarification(
            retriever=None,
            user_query=QUERY,
            search_query=QUERY,
            product_intent="Adobe Data Collection",
            blocked_reason="no_direct_match",
            refinement=RefinementResult(gap_reasons=["documentation_vocabulary_mismatch"]),
            related_docs=[],
        )
        assert result is not None
        assert len(result.options) == 1

    def test_clarification_selection_routing(self):
        routing = clarification_selection_to_routing({
            "option_id": "opt-1",
            "resolved_query": "How do I install Meta Pixel?",
            "product_override": "Adobe Experience Platform",
            "doc_anchor_s3_key": "adobe-docs/data-collection/help/tags/meta/overview.md",
        })
        assert routing["skip_topical_gate"] is True
        assert routing["product_override"] == "Adobe Experience Platform"

    def test_event_payload_shape(self, monkeypatch):
        monkeypatch.setattr(
            "backend.core.clarification_resolver._probe_neighbors",
            lambda *_args, **_kwargs: [
                _neighbor("Meta Pixel Extension Overview", "Adobe Experience Platform"),
            ],
        )
        result = build_clarification(
            retriever=None,
            user_query=QUERY,
            search_query=QUERY,
            product_intent="Adobe Data Collection",
            blocked_reason="no_direct_match",
            refinement=RefinementResult(gap_reasons=["product_filter_excluded_stronger_neighbors"]),
            related_docs=[],
        )
        payload = result.to_event_payload()
        assert payload["type"] == "clarification"
        assert payload["original_query"] == QUERY
        assert len(payload["options"]) >= 1
        assert "id" in payload["options"][0]
        assert "similarity_score" in payload["options"][0]
        assert "match_strength" in payload["options"][0]
