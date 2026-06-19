"""Tests for Educator Mode v2 domain selector and readiness report."""

from backend.core.domain_selector import select_next_domain
from backend.core.readiness_report import generate_readiness_report
from config.exams import get_exam


def test_select_next_domain_favors_highest_weight_first():
    exam = get_exam("AD0-E212")
    assert exam is not None
    domain = select_next_domain(exam, {})
    assert domain.id == "business-analysis"


def test_readiness_report_uses_first_try_for_verdict():
    exam = get_exam("AD0-E212")
    assert exam is not None
    questions = [
        {
            "questionId": "q1",
            "domainId": "business-analysis",
            "resolved": True,
            "skipped": False,
            "attempts": [{"answer": "B", "correct": False}, {"answer": "A", "correct": True}],
        },
        {
            "questionId": "q2",
            "domainId": "business-analysis",
            "resolved": True,
            "skipped": False,
            "attempts": [{"answer": "C", "correct": True}],
        },
    ]
    report = generate_readiness_report(exam, questions=questions)
    assert report.overall_pct == 100
    assert report.first_try_pct == 50
    assert report.total_skipped == 0


def test_readiness_report_skip_not_counted_as_wrong():
    exam = get_exam("AD0-E212")
    assert exam is not None
    questions = [
        {
            "questionId": "q1",
            "domainId": "segmentation",
            "domain": "Segmentation",
            "questionText": "Skipped Q",
            "resolved": False,
            "skipped": True,
            "attempts": [],
        },
    ]
    report = generate_readiness_report(exam, questions=questions)
    assert report.total_skipped == 1
    assert report.total_resolved == 0
