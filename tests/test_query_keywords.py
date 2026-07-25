"""Tests for structured keyword extraction and hybrid scoring."""

from backend.core.query_keywords import (
    extract_query_keywords,
    hybrid_doc_score,
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


def _scored_doc(title: str, content: str, url: str, score: float):
    return {
        "content": content,
        "score": score,
        "metadata": {"title": title, "url": url, "s3_key": url},
    }


class TestSingleTermCollisionDampening:
    """hybrid_doc_score's keyword component (keyword_match_score) computes
    term_hits/term_total — with only 1 match_term, any incidental hit
    saturates that ratio to 1.0 regardless of true relevance (the same shape
    as the historical "Calculated Metrics" bug, but for "segment"/"profile"/
    "identity" rather than "calculated" — words too meaningful to exclude via
    a stopword list, unlike "calculated"). _MIN_RELIABLE_TERM_TOTAL dampens
    the keyword weight instead of trying to stopword-list every such word.
    """

    def test_calculated_metrics_regression_resolves_via_structural_fix(self):
        """The original bug case: 'orders calculated in AEP Web SDK' ranking
        Calculated Metrics Overview above Order Data Type (XDM). Structural
        dampening alone (independent of the "calculated" stopword) must
        resolve this."""
        order_doc = _scored_doc(
            "Order Data Type (XDM)",
            "The Order data type represents commerce order fields collected via the AEP Web SDK.",
            "https://experienceleague.adobe.com/docs/xdm/schema/order.html",
            score=0.45,
        )
        calc_metrics_doc = _scored_doc(
            "Calculated Metrics Overview",
            "Calculated metrics let you combine existing metrics using math operators for custom reporting.",
            "https://experienceleague.adobe.com/docs/analytics/components/calculated-metrics/overview.html",
            score=0.15,
        )
        kw = extract_query_keywords("orders calculated in AEP Web SDK")
        assert hybrid_doc_score(order_doc, kw, "orders calculated in AEP Web SDK") > hybrid_doc_score(
            calc_metrics_doc, kw, "orders calculated in AEP Web SDK"
        )

    def test_segment_single_term_does_not_inflate_unrelated_doc(self):
        query = "segment setup steps"
        relevant = _scored_doc(
            "Real-Time CDP Audience Composition and Activation",
            "Compose audiences in Real-Time CDP for activation to downstream destinations.",
            "https://x/rtcdp-audience",
            score=0.5,
        )
        unrelated = _scored_doc(
            "Segment Overview for Adobe Analytics",
            "An audience segment groups visitors sharing common traits for reporting purposes.",
            "https://x/analytics-segment",
            score=0.1,
        )
        kw = extract_query_keywords(query)
        assert hybrid_doc_score(relevant, kw, query) > hybrid_doc_score(unrelated, kw, query)

    def test_profile_single_term_does_not_inflate_unrelated_doc(self):
        query = "profile setup steps"
        relevant = _scored_doc(
            "Profile Merge Policies in Real-Time CDP",
            "Configure merge policies to control how profile fragments are combined.",
            "https://x/rtcdp-merge-policies",
            score=0.5,
        )
        unrelated = _scored_doc(
            "User Profile Settings in Adobe Admin Console",
            "Manage your personal user profile display name and avatar.",
            "https://x/admin-console-profile",
            score=0.1,
        )
        kw = extract_query_keywords(query)
        assert hybrid_doc_score(relevant, kw, query) > hybrid_doc_score(unrelated, kw, query)

    def test_identity_single_term_does_not_inflate_unrelated_doc(self):
        query = "identity setup steps"
        relevant = _scored_doc(
            "Identity Graph and Namespace Configuration",
            "Configure identity namespaces for the AEP Identity Graph.",
            "https://x/aep-identity-graph",
            score=0.5,
        )
        unrelated = _scored_doc(
            "Brand Identity Guidelines for Marketing Assets",
            "Use these brand identity guidelines for logo placement.",
            "https://x/brand-identity-guidelines",
            score=0.1,
        )
        kw = extract_query_keywords(query)
        assert hybrid_doc_score(relevant, kw, query) > hybrid_doc_score(unrelated, kw, query)

    def test_genuine_single_term_kw_rescue_not_over_dampened(self):
        """A genuinely on-topic doc with a weak/misleading embedding score
        (paraphrase-vocabulary mismatch) must still be rescued by a strong
        single-term keyword match, even though that same term list length
        triggers dampening — the dampening factor must not be so aggressive
        that it erases legitimate rescue signal."""
        query = "webhook setup steps"
        relevant = _scored_doc(
            "Configuring Webhooks for Real-Time Event Notifications",
            "Set up a webhook endpoint to receive real-time notifications.",
            "https://x/webhook-config",
            score=0.18,
        )
        # Embedding score coincidentally favors the wrong, unrelated doc.
        unrelated_higher_embed = _scored_doc(
            "Real-Time Customer Profile Overview",
            "The Real-Time Customer Profile unifies known and anonymous data.",
            "https://x/rtcp-overview",
            score=0.30,
        )
        kw = extract_query_keywords(query)
        assert hybrid_doc_score(relevant, kw, query) > hybrid_doc_score(
            unrelated_higher_embed, kw, query
        )
