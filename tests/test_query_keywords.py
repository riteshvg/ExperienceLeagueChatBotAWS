"""Tests for structured keyword extraction and hybrid scoring."""

from backend.core.query_keywords import (
    extract_query_keywords,
    keyword_match_score,
)


def _doc(title: str, content: str = "", url: str = ""):
    return {
        "content": content,
        "score": 0.4,
        "metadata": {
            "title": title,
            "url": url,
            "s3_key": url,
            "product": "Adobe Data Collection",
        },
    }


class TestQueryKeywords:
    def test_adv_pixels_phrase_and_synonyms(self):
        kw = extract_query_keywords(
            "How to implement ADV pixels in Adobe Data Collection?",
            "Adobe Data Collection",
        )
        assert any("adv" in p.lower() for p in kw.topic_phrases)
        assert "advertising" in [t.lower() for t in kw.match_terms]
        assert "pixel" in [t.lower() for t in kw.match_terms]
        assert len(kw.embedding_queries) >= 2
        assert any("advertising" in q.lower() for q in kw.embedding_queries)

    def test_trade_desk_phrase(self):
        kw = extract_query_keywords(
            "How to implement The Trade Desk scripts inside adobe launch",
            "Adobe Data Collection",
        )
        assert any("trade desk" in p.lower() for p in kw.topic_phrases)
        assert any("tags" in t.lower() for t in kw.match_terms)

    def test_keyword_match_scores_meta_pixel_higher(self):
        kw = extract_query_keywords("How to implement ADV pixels in Adobe Data Collection?")
        meta = _doc(
            "Meta Pixel Extension Overview",
            "Configure the advertising pixel extension for Adobe Tags.",
            "https://experienceleague.adobe.com/en/docs/experience-platform/tags/extensions/advertising/meta/overview",
        )
        datastream = _doc(
            "Configure a datastream for Platform Mobile SDK implementations",
            "Datastreams can be created in the Data Collection interface.",
        )
        assert keyword_match_score(kw, meta) > keyword_match_score(kw, datastream)


class TestGenericAcronymPairingRegression:
    """
    Regression: "{ACRONYM} {generic noun}" topic phrases (e.g. "AEP request",
    "CJA data") combined with the full product name produced a near content-free
    embedding probe (e.g. "AEP request Adobe Experience Platform") that scored
    high against ANY doc dominated by the product's own boilerplate (release
    notes, overviews) — drowning out genuinely relevant docs in the hybrid merge
    and causing real questions to fall through to "no_direct_match".
    """

    def test_acronym_plus_generic_noun_skips_product_combo_query(self):
        kw = extract_query_keywords(
            "We are seeing an AEP request call/Dispatch consequence event call "
            "and 2 post processed analytics call with different request ids "
            "because of this we are seeing double counts in report. "
            "What is the issue here?",
            "Adobe Experience Platform",
        )
        assert "AEP request" in kw.topic_phrases
        assert "AEP request Adobe Experience Platform" not in kw.embedding_queries
        # The bare phrase probe should still be present.
        assert "AEP request" in kw.embedding_queries

    def test_cja_data_skips_product_combo_query(self):
        kw = extract_query_keywords(
            "What is a CJA data view?",
            "Customer Journey Analytics",
        )
        assert "CJA data" in kw.topic_phrases
        assert "CJA data Customer Journey Analytics" not in kw.embedding_queries

    def test_distinctive_acronym_phrase_still_gets_product_combo_query(self):
        """Genuinely distinctive phrases (not a bare acronym + generic noun)
        should still be combined with the product name — only the noisy
        acronym+generic-noun pairing is suppressed."""
        kw = extract_query_keywords(
            "How do I implement ADV pixels in Adobe Tags?",
            "Adobe Data Collection",
        )
        assert any(
            q.startswith("ADV pixels") and q.endswith("Adobe Data Collection")
            for q in kw.embedding_queries
        )

    def test_trade_desk_still_gets_product_combo_query(self):
        kw = extract_query_keywords(
            "How do I set up Trade Desk scripts?",
            "Adobe Data Collection",
        )
        assert "Trade Desk Adobe Data Collection" in kw.embedding_queries
