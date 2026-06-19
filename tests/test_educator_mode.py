"""Tests for Educator Mode domain selector and readiness report."""

from backend.core.domain_selector import select_next_domain
from backend.core.readiness_report import generate_readiness_report
from config.exams import get_exam


def test_select_next_domain_favors_highest_weight_first():
    exam = get_exam("AD0-E212")
    assert exam is not None
    domain = select_next_domain(exam, {})
    assert domain.id == "business-analysis"


def test_select_next_domain_balances_over_session():
    exam = get_exam("AD0-E212")
    assert exam is not None
    scores = {
        "business-analysis": {"correct": 3, "total": 3},
        "reporting-dashboarding": {"correct": 0, "total": 0},
    }
    domain = select_next_domain(exam, scores)
    assert domain.id in {"reporting-dashboarding", "segmentation", "tool-knowledge"}


def test_readiness_report_verdict_ready():
    exam = get_exam("AD0-E212")
    assert exam is not None
    report = generate_readiness_report(
        exam,
        {"business-analysis": {"correct": 8, "total": 10}},
        total_correct=8,
        total_asked=10,
    )
    assert report.overall_pct == 80
    assert report.verdict == "Ready"


def test_readiness_report_flags_weak_domain():
    exam = get_exam("AD0-E212")
    assert exam is not None
    report = generate_readiness_report(
        exam,
        {
            "business-analysis": {"correct": 0, "total": 3},
            "reporting-dashboarding": {"correct": 3, "total": 3},
        },
        total_correct=3,
        total_asked=6,
    )
    weak = [d for d in report.domain_reports if d.weak]
    assert any(d.domain_id == "business-analysis" for d in weak)
