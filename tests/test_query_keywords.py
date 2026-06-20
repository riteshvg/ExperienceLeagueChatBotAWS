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
