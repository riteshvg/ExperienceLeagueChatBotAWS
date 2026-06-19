"""Adobe certification exam registry for Educator Mode."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ExamLevel = Literal["Professional", "Expert", "Master"]


@dataclass(frozen=True)
class ExamDomain:
    id: str
    name: str
    weight_pct: int
    doc_search_hint: str


@dataclass(frozen=True)
class Exam:
    id: str
    name: str
    product: str
    level: ExamLevel
    total_questions: int
    passing_score: int
    time_limit_mins: int
    domains: tuple[ExamDomain, ...]


EXAMS: tuple[Exam, ...] = (
    Exam(
        id="AD0-E212",
        name="Analytics Business Practitioner Professional",
        product="Adobe Analytics",
        level="Professional",
        total_questions=50,
        passing_score=31,
        time_limit_mins=100,
        domains=(
            ExamDomain(
                id="business-analysis",
                name="Business analysis",
                weight_pct=31,
                doc_search_hint=(
                    "KPI business requirements conversion funnels report suite analysis workspace"
                ),
            ),
            ExamDomain(
                id="reporting-dashboarding",
                name="Reporting and dashboarding",
                weight_pct=23,
                doc_search_hint=(
                    "Analysis Workspace visualizations fallout flow Report Builder scheduling"
                ),
            ),
            ExamDomain(
                id="segmentation",
                name="Segmentation and calculated metrics",
                weight_pct=23,
                doc_search_hint="segment builder containers hit visit visitor calculated metrics",
            ),
            ExamDomain(
                id="tool-knowledge",
                name="General tool knowledge and troubleshooting",
                weight_pct=23,
                doc_search_hint=(
                    "data quality traffic spike admin console report suite settings dimensions"
                ),
            ),
        ),
    ),
    Exam(
        id="AD0-E202",
        name="Analytics Business Practitioner Expert",
        product="Adobe Analytics",
        level="Expert",
        total_questions=69,
        passing_score=49,
        time_limit_mins=120,
        domains=(
            ExamDomain(
                id="business-analysis",
                name="Business analysis",
                weight_pct=25,
                doc_search_hint=(
                    "business requirements SDR KPI conversion funnel outliers anomalies"
                ),
            ),
            ExamDomain(
                id="reporting-dashboarding",
                name="Reporting and dashboarding for projects",
                weight_pct=25,
                doc_search_hint=(
                    "workspace projects fallout flow Data Warehouse Report Builder alerts"
                ),
            ),
            ExamDomain(
                id="segmentation",
                name="Segmentation and calculated metrics",
                weight_pct=25,
                doc_search_hint="segment builder calculated metrics participation metric types",
            ),
            ExamDomain(
                id="tool-knowledge",
                name="General tool knowledge and troubleshooting",
                weight_pct=15,
                doc_search_hint="dimensions eVars props data quality troubleshooting data feeds",
            ),
            ExamDomain(
                id="administration",
                name="Administration",
                weight_pct=10,
                doc_search_hint=(
                    "marketing channels classification importer virtual report suite "
                    "admin console processing rules"
                ),
            ),
        ),
    ),
    Exam(
        id="AD0-E213",
        name="Analytics Developer Professional",
        product="Adobe Analytics",
        level="Professional",
        total_questions=50,
        passing_score=31,
        time_limit_mins=100,
        domains=(
            ExamDomain(
                id="implementation",
                name="Analytics implementation and configuration",
                weight_pct=30,
                doc_search_hint=(
                    "AppMeasurement deploy code report suite variable settings data layer"
                ),
            ),
            ExamDomain(
                id="tag-management",
                name="Tag management systems",
                weight_pct=18,
                doc_search_hint=(
                    "Adobe Launch Experience Platform Tags rules data elements extensions audit"
                ),
            ),
            ExamDomain(
                id="testing-validation",
                name="Testing, validation and troubleshooting",
                weight_pct=18,
                doc_search_hint=(
                    "JavaScript errors Adobe Debugger server call beacon validation debugging"
                ),
            ),
            ExamDomain(
                id="ecosystem",
                name="Experience Cloud ecosystem and identity",
                weight_pct=14,
                doc_search_hint=(
                    "Experience Cloud ID service ECID identity integrations Adobe Launch tags overview"
                ),
            ),
            ExamDomain(
                id="solution-design",
                name="Solution design reference and strategy",
                weight_pct=12,
                doc_search_hint="solution design reference SDR tech spec data objects variable mapping",
            ),
            ExamDomain(
                id="mobile-api",
                name="Mobile services and API",
                weight_pct=8,
                doc_search_hint="Analytics API 2.0 data feed data warehouse mobile SDK processing rules",
            ),
        ),
    ),
)


def get_exam(exam_id: str) -> Exam | None:
    for exam in EXAMS:
        if exam.id == exam_id:
            return exam
    return None


def exams_for_api() -> list[dict]:
    """Serialize exams for JSON API responses."""
    return [
        {
            "id": e.id,
            "name": e.name,
            "product": e.product,
            "level": e.level,
            "totalQuestions": e.total_questions,
            "passingScore": e.passing_score,
            "timeLimitMins": e.time_limit_mins,
            "domains": [
                {
                    "id": d.id,
                    "name": d.name,
                    "weightPct": d.weight_pct,
                    "docSearchHint": d.doc_search_hint,
                }
                for d in e.domains
            ],
        }
        for e in EXAMS
    ]
