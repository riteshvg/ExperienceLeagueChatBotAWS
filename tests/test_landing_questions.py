from backend.core.landing_questions import (
    SOLUTION_ANALYTICS,
    SOLUTION_AEP,
    SOLUTION_CJA,
    SOLUTION_CROSS,
    SOLUTION_DATA_COLLECTION,
    SOLUTION_GENERAL,
    ALL_TAB_PER_SOLUTION,
    MAX_PER_SOLUTION,
    classify_solution,
    group_landing_questions,
)


def test_classify_single_product():
    assert classify_solution("How do I create a segment in Adobe Analytics?") == SOLUTION_ANALYTICS
    assert classify_solution("What is a Data View in Customer Journey Analytics?") == SOLUTION_CJA
    assert classify_solution("How do I create an XDM schema in AEP?") == SOLUTION_AEP


def test_classify_cross_product():
    assert (
        classify_solution("How does data flow from Adobe Analytics to Customer Journey Analytics?")
        == SOLUTION_CROSS
    )


def test_classify_data_collection():
    assert classify_solution("How do I configure Adobe Tags extensions for Launch?") == SOLUTION_DATA_COLLECTION


def test_classify_topic_hint():
    assert classify_solution("How do I set up an eVar for campaign tracking?") == SOLUTION_ANALYTICS
    assert classify_solution("How do I create a segment definition for profiles?") == SOLUTION_AEP


def test_classify_general():
    assert classify_solution("hello") is None
    assert classify_solution("How do I troubleshoot missing data in my reports?") == SOLUTION_GENERAL


def test_group_landing_questions_dedupes_and_caps():
    rows = [
        {"query_text": "How do I create a segment in Adobe Analytics?", "times_asked": 3},
        {"query_text": "how do i create a segment in adobe analytics?", "times_asked": 1},
        {"query_text": "What is a Data View in Customer Journey Analytics?", "times_asked": 2},
    ]
    payload = group_landing_questions(rows, per_solution=5)
    assert payload["total"] == 2
    assert len(payload["by_solution"][SOLUTION_ANALYTICS]) == 1
    assert len(payload["by_solution"][SOLUTION_CJA]) == 1


def test_limits_constants():
    assert ALL_TAB_PER_SOLUTION == 4
    assert MAX_PER_SOLUTION == 15
