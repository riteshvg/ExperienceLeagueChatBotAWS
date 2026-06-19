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
    concept_anchors: tuple[str, ...]


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
                    "AppMeasurement deploy code report suite variable settings data layer s.t() s.tl()"
                ),
                concept_anchors=(
                    "AppMeasurement lifecycle",
                    "data layer pattern",
                    "variable population order",
                    "report suite configuration",
                    "hit sending",
                ),
            ),
            ExamDomain(
                id="tag-management",
                name="Tag management systems",
                weight_pct=18,
                doc_search_hint=(
                    "Adobe Launch Experience Platform Tags rules data elements extensions publish flow"
                ),
                concept_anchors=(
                    "Launch rules",
                    "data elements",
                    "extension configuration",
                    "publish workflow",
                    "tag auditing",
                ),
            ),
            ExamDomain(
                id="testing-validation",
                name="Testing, validation and troubleshooting",
                weight_pct=18,
                doc_search_hint=(
                    "Adobe Debugger JavaScript errors beacon validation server call lifecycle Charles"
                ),
                concept_anchors=(
                    "Adobe Debugger",
                    "beacon inspection",
                    "JS error types",
                    "validation workflow",
                    "data quality checks",
                ),
            ),
            ExamDomain(
                id="ecosystem",
                name="Experience Cloud ecosystem and identity",
                weight_pct=14,
                doc_search_hint=(
                    "Experience Cloud ID ECID identity service visitor ID cross-solution integrations"
                ),
                concept_anchors=(
                    "ECID",
                    "Experience Cloud ID service",
                    "visitor stitching",
                    "cross-solution data sharing",
                    "identity graph",
                ),
            ),
            ExamDomain(
                id="solution-design",
                name="Solution design reference and strategy",
                weight_pct=12,
                doc_search_hint=(
                    "solution design reference SDR tech spec variable mapping business requirements"
                ),
                concept_anchors=(
                    "SDR structure",
                    "variable taxonomy",
                    "requirements translation",
                    "eVar/prop selection",
                    "documentation standards",
                ),
            ),
            ExamDomain(
                id="mobile-api",
                name="Mobile services and API",
                weight_pct=8,
                doc_search_hint=(
                    "Analytics API 2.0 data feed data warehouse mobile SDK AEP Mobile processing rules"
                ),
                concept_anchors=(
                    "Analytics API endpoints",
                    "data feed columns",
                    "mobile SDK lifecycle",
                    "processing rules order",
                    "data warehouse filters",
                ),
            ),
        ),
    ),
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
                    "KPI business requirements conversion funnels report suite analysis workspace outliers"
                ),
                concept_anchors=(
                    "KPI translation",
                    "conversion funnel analysis",
                    "anomaly detection",
                    "report suite strategy",
                    "SDR interpretation",
                ),
            ),
            ExamDomain(
                id="reporting-dashboarding",
                name="Reporting and dashboarding",
                weight_pct=23,
                doc_search_hint=(
                    "Analysis Workspace visualizations fallout flow Report Builder scheduling Data Warehouse"
                ),
                concept_anchors=(
                    "Workspace panels",
                    "fallout vs flow",
                    "Report Builder scheduling",
                    "Data Warehouse use cases",
                    "alert configuration",
                ),
            ),
            ExamDomain(
                id="segmentation",
                name="Segmentation and calculated metrics",
                weight_pct=23,
                doc_search_hint=(
                    "segment builder containers hit visit visitor calculated metrics participation"
                ),
                concept_anchors=(
                    "segment containers",
                    "sequential segmentation",
                    "calculated metric types",
                    "segment stacking",
                    "metric participation",
                ),
            ),
            ExamDomain(
                id="tool-knowledge",
                name="General tool knowledge and troubleshooting",
                weight_pct=23,
                doc_search_hint=(
                    "data quality traffic spike admin console dimensions eVars props data feeds classifications"
                ),
                concept_anchors=(
                    "dimension types",
                    "eVar vs prop",
                    "data quality investigation",
                    "classification setup",
                    "data feed structure",
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
                    "business requirements SDR KPI conversion funnel outliers anomaly detection"
                ),
                concept_anchors=(
                    "advanced KPI mapping",
                    "multi-suite strategy",
                    "anomaly investigation",
                    "hypothesis building",
                    "SDR authoring",
                ),
            ),
            ExamDomain(
                id="reporting-dashboarding",
                name="Reporting and dashboarding for projects",
                weight_pct=25,
                doc_search_hint=(
                    "workspace projects fallout flow Data Warehouse Report Builder alerts sharing"
                ),
                concept_anchors=(
                    "advanced Workspace",
                    "Data Warehouse queries",
                    "Report Builder automation",
                    "project sharing governance",
                    "curated reports",
                ),
            ),
            ExamDomain(
                id="segmentation",
                name="Segmentation and calculated metrics",
                weight_pct=25,
                doc_search_hint=(
                    "segment builder calculated metrics participation metric types advanced containers"
                ),
                concept_anchors=(
                    "advanced segmentation",
                    "sequential segments",
                    "metric participation",
                    "calculated metric functions",
                    "segment comparison",
                ),
            ),
            ExamDomain(
                id="tool-knowledge",
                name="General tool knowledge and troubleshooting",
                weight_pct=15,
                doc_search_hint=(
                    "dimensions eVars props data quality troubleshooting data feeds attribution"
                ),
                concept_anchors=(
                    "attribution models",
                    "data feed processing",
                    "advanced troubleshooting",
                    "variable persistence",
                    "data governance",
                ),
            ),
            ExamDomain(
                id="administration",
                name="Administration",
                weight_pct=10,
                doc_search_hint=(
                    "marketing channels classification importer virtual report suite admin console "
                    "processing rules VISTA"
                ),
                concept_anchors=(
                    "marketing channel rules",
                    "classification rule builder",
                    "virtual report suites",
                    "VISTA rules",
                    "admin console governance",
                ),
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
                    "conceptAnchors": list(d.concept_anchors),
                }
                for d in e.domains
            ],
        }
        for e in EXAMS
    ]
