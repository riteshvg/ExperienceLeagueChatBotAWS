"""Readiness report calculator for Educator Mode v2."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from config.exams import Exam

Verdict = Literal["Ready to attempt", "Almost there", "Keep going"]


@dataclass
class DomainReport:
    domain: str
    domain_id: str
    correct: int
    total: int
    skipped: int
    pct: int
    weak: bool
    doc_search_hint: str


@dataclass
class ReadinessReport:
    overall_pct: int
    first_try_pct: int
    passing_pct: int
    total_correct: int
    total_resolved: int
    total_skipped: int
    verdict: Verdict
    domain_reports: list[DomainReport]
    skipped_questions: list[dict[str, Any]]


def _question_dicts(questions: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    return questions or []


def generate_readiness_report(
    exam: Exam,
    domain_scores: dict[str, dict[str, int]] | None = None,
    questions: list[dict[str, Any]] | None = None,
    total_correct: int | None = None,
    total_asked: int | None = None,
) -> ReadinessReport:
    """Build readiness report from question records (preferred) or legacy domain_scores."""
    qlist = _question_dicts(questions)
    passing_pct = round((exam.passing_score / exam.total_questions) * 100)

    if qlist:
        resolved = [q for q in qlist if q.get("resolved") and not q.get("skipped")]
        skipped = [q for q in qlist if q.get("skipped")]
        total_resolved = len(resolved)
        total_correct = sum(
            1 for q in resolved if any(a.get("correct") for a in q.get("attempts", []))
        )
        first_try_correct = sum(
            1 for q in resolved if q.get("attempts") and q["attempts"][0].get("correct")
        )
        total_skipped = len(skipped)
    else:
        scores = domain_scores or {}
        total_resolved = total_asked or sum(d.get("total", 0) for d in scores.values())
        total_correct = total_correct if total_correct is not None else sum(
            d.get("correct", 0) for d in scores.values()
        )
        first_try_correct = total_correct
        total_skipped = sum(d.get("skipped", 0) for d in scores.values())
        skipped = []

    overall_pct = round((total_correct / total_resolved) * 100) if total_resolved > 0 else 0
    first_try_pct = (
        round((first_try_correct / total_resolved) * 100) if total_resolved > 0 else 0
    )

    domain_reports: list[DomainReport] = []
    for domain in exam.domains:
        if qlist:
            domain_qs = [q for q in qlist if q.get("domainId") == domain.id]
            resolved_d = [q for q in domain_qs if q.get("resolved") and not q.get("skipped")]
            correct = sum(
                1 for q in resolved_d if any(a.get("correct") for a in q.get("attempts", []))
            )
            total = len(resolved_d)
            skipped_count = sum(1 for q in domain_qs if q.get("skipped"))
        else:
            scores = (domain_scores or {}).get(domain.id, {"correct": 0, "total": 0, "skipped": 0})
            correct = scores.get("correct", 0)
            total = scores.get("total", 0)
            skipped_count = scores.get("skipped", 0)

        pct = round((correct / total) * 100) if total > 0 else 0
        domain_reports.append(
            DomainReport(
                domain=domain.name,
                domain_id=domain.id,
                correct=correct,
                total=total,
                skipped=skipped_count,
                pct=pct,
                weak=total >= 2 and pct < passing_pct,
                doc_search_hint=domain.doc_search_hint,
            )
        )

    domain_reports.sort(key=lambda d: (not d.weak, d.pct))

    # Verdict driven by first-try accuracy (exam-realistic signal)
    if first_try_pct >= passing_pct + 10:
        verdict = "Ready to attempt"
    elif first_try_pct >= passing_pct - 5:
        verdict = "Almost there"
    else:
        verdict = "Keep going"

    skipped_questions = [
        {
            "questionId": q.get("questionId", ""),
            "domainId": q.get("domainId", ""),
            "questionText": q.get("questionText", ""),
            "domain": q.get("domain", ""),
        }
        for q in skipped
    ]

    return ReadinessReport(
        overall_pct=overall_pct,
        first_try_pct=first_try_pct,
        passing_pct=passing_pct,
        total_correct=total_correct,
        total_resolved=total_resolved,
        total_skipped=total_skipped,
        verdict=verdict,
        domain_reports=domain_reports,
        skipped_questions=skipped_questions,
    )


def readiness_report_to_dict(report: ReadinessReport) -> dict:
    return {
        "overallPct": report.overall_pct,
        "firstTryPct": report.first_try_pct,
        "passingPct": report.passing_pct,
        "totalCorrect": report.total_correct,
        "totalResolved": report.total_resolved,
        "totalSkipped": report.total_skipped,
        "totalAsked": report.total_resolved,
        "verdict": report.verdict,
        "domainReports": [
            {
                "domain": d.domain,
                "domainId": d.domain_id,
                "correct": d.correct,
                "total": d.total,
                "skipped": d.skipped,
                "pct": d.pct,
                "weak": d.weak,
                "docSearchHint": d.doc_search_hint,
            }
            for d in report.domain_reports
        ],
        "skippedQuestions": report.skipped_questions,
    }
