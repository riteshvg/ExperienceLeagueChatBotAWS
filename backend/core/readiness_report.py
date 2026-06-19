"""Readiness report calculator for Educator Mode /score command."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from config.exams import Exam

Verdict = Literal["Ready", "Almost ready", "Needs more prep"]


@dataclass
class DomainReport:
    domain: str
    domain_id: str
    correct: int
    total: int
    pct: int
    weak: bool
    doc_search_hint: str


@dataclass
class ReadinessReport:
    overall_pct: int
    passing_pct: int
    total_correct: int
    total_asked: int
    verdict: Verdict
    domain_reports: list[DomainReport]


def generate_readiness_report(
    exam: Exam,
    domain_scores: dict[str, dict[str, int]],
    total_correct: int | None = None,
    total_asked: int | None = None,
) -> ReadinessReport:
    if total_asked is None:
        total_asked = sum(d.get("total", 0) for d in domain_scores.values())
    if total_correct is None:
        total_correct = sum(d.get("correct", 0) for d in domain_scores.values())

    overall_pct = round((total_correct / total_asked) * 100) if total_asked > 0 else 0
    passing_pct = round((exam.passing_score / exam.total_questions) * 100)

    domain_reports: list[DomainReport] = []
    for domain in exam.domains:
        scores = domain_scores.get(domain.id, {"correct": 0, "total": 0})
        correct = scores.get("correct", 0)
        total = scores.get("total", 0)
        pct = round((correct / total) * 100) if total > 0 else 0
        domain_reports.append(
            DomainReport(
                domain=domain.name,
                domain_id=domain.id,
                correct=correct,
                total=total,
                pct=pct,
                weak=pct < passing_pct and total >= 2,
                doc_search_hint=domain.doc_search_hint,
            )
        )

    if overall_pct >= passing_pct + 10:
        verdict = "Ready"
    elif overall_pct >= passing_pct - 5:
        verdict = "Almost ready"
    else:
        verdict = "Needs more prep"

    return ReadinessReport(
        overall_pct=overall_pct,
        passing_pct=passing_pct,
        total_correct=total_correct,
        total_asked=total_asked,
        verdict=verdict,
        domain_reports=domain_reports,
    )


def readiness_report_to_dict(report: ReadinessReport) -> dict:
    return {
        "overallPct": report.overall_pct,
        "passingPct": report.passing_pct,
        "totalCorrect": report.total_correct,
        "totalAsked": report.total_asked,
        "verdict": report.verdict,
        "domainReports": [
            {
                "domain": d.domain,
                "domainId": d.domain_id,
                "correct": d.correct,
                "total": d.total,
                "pct": d.pct,
                "weak": d.weak,
                "docSearchHint": d.doc_search_hint,
            }
            for d in report.domain_reports
        ],
    }
