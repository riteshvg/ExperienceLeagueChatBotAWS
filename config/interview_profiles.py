"""
Interview prep question banks for Interviewer Mode.

Levels × solutions (or Principal collections) with topic metadata for retrieval.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

InterviewLevel = Literal["junior", "senior", "architect", "principal"]

LEVELS: tuple[dict[str, str], ...] = (
    {"id": "junior", "label": "Junior", "description": "0–2 years, foundational concepts"},
    {"id": "senior", "label": "Senior", "description": "3–5 years, hands-on implementation"},
    {"id": "architect", "label": "Architect", "description": "5+ years, design and trade-offs"},
    {"id": "principal", "label": "Principal", "description": "Cross-solution leadership and strategy"},
)

SOLUTIONS: tuple[dict[str, str], ...] = (
    {
        "id": "all",
        "label": "All solutions",
        "short": "All",
        "description": "Mixed questions across CJA, AEP, Web SDK, Target, and AJO",
    },
    {"id": "cja", "label": "Customer Journey Analytics", "short": "CJA"},
    {"id": "aep", "label": "Adobe Experience Platform", "short": "AEP"},
    {"id": "web_sdk", "label": "Web SDK / Data Collection", "short": "Web SDK"},
    {"id": "target", "label": "Adobe Target", "short": "Target"},
    {"id": "ajo", "label": "Adobe Journey Optimizer", "short": "AJO"},
)

# Multi-solution collections. Most are Principal-only, but a collection may
# declare more than one eligible level via "levels" (e.g. scenario_troubleshooting,
# which is available at senior, architect, and principal from the same stored
# question set — see the 'multi' level sentinel in google_db.get_active_question_bank).
COLLECTIONS: tuple[dict, ...] = (
    {
        "id": "all",
        "label": "All collections",
        "description": "Mixed questions from every Principal cross-solution track",
        "levels": ("junior", "senior", "architect", "principal"),
    },
    {
        "id": "cross_solution_architecture",
        "label": "Cross-Solution Architecture",
        "description": "AEP → CJA → Activation data flows and governance",
        "levels": ("principal",),
    },
    {
        "id": "data_foundation",
        "label": "Data Foundation & Identity",
        "description": "Schemas, identity graphs, and stitching across products",
        "levels": ("principal",),
    },
    {
        "id": "personalization_stack",
        "label": "Personalization Stack",
        "description": "Target, AJO, and Real-Time CDP activation patterns",
        "levels": ("principal",),
    },
    {
        "id": "scenario_troubleshooting",
        "label": "Scenario Troubleshooting",
        "description": "Cross-product incident/design scenarios spanning AJO, AEP, identity, segmentation, governance, and decisioning",
        "levels": ("principal",),
    },
)

# Levels where scenario_troubleshooting isn't a standalone selectable focus —
# its questions are folded into the "All solutions" mix instead (see
# _fetch_bank), so senior/architect users get scenario questions without a
# separate card cluttering the solution-focus picker.
_SCENARIO_FOLDED_LEVELS = ("senior", "architect")


@dataclass(frozen=True)
class InterviewQuestion:
    id: str
    question: str
    topic: str
    difficulty: int
    expected_themes: tuple[str, ...]
    retrieval_hint: str
    version: int = 1
    is_followup: bool = False
    question_type: str = "standard"
    grading_rubric: dict | None = None


def _q(
    id: str,
    question: str,
    topic: str,
    difficulty: int,
    themes: tuple[str, ...],
    hint: str,
) -> InterviewQuestion:
    return InterviewQuestion(id, question, topic, difficulty, themes, hint)


def _scenario_q(
    id: str,
    question: str,
    topic: str,
    difficulty: int,
    hint: str,
    rubric: dict,
) -> InterviewQuestion:
    """Scenario question graded from a structured, weighted rubric (see
    interviewer_pipeline._score_from_rubric_match) instead of the generic
    expected_themes list used by standard questions."""
    return InterviewQuestion(
        id, question, topic, difficulty, (), hint,
        question_type="scenario", grading_rubric=rubric,
    )


# ── CJA ───────────────────────────────────────────────────────────────────────

_CJA_JUNIOR = (
    _q("cja-j1", "What is Customer Journey Analytics and how does it differ from Adobe Analytics?", "overview", 2,
       ("reporting time", "person-centric", "Analysis Workspace"), "Customer Journey Analytics overview"),
    _q("cja-j2", "What is a data view in CJA and why is it required?", "data_views", 2,
       ("schema", "dimensions", "metrics", "sessionization"), "CJA data view create"),
    _q("cja-j3", "What is a connection in CJA?", "connections", 2,
       ("Adobe Analytics", "Experience Event", "dataset"), "CJA connection setup"),
    _q("cja-j4", "Name two ways you can bring data into CJA.", "ingestion", 2,
       ("Analytics", "AEP", "Experience Event"), "CJA data sources connections"),
    _q("cja-j5", "What is Analysis Workspace in CJA used for?", "workspace", 1,
       ("panels", "visualizations", "freeform"), "CJA Analysis Workspace"),
)

_CJA_SENIOR = (
    _q("cja-s1", "Explain the difference between calculated metrics and derived fields in CJA.", "metrics", 3,
       ("report time", "event time", "filters", "functions"), "calculated metrics derived fields CJA"),
    _q("cja-s2", "How would you design a data view for cross-channel journey analysis?", "data_views", 4,
       ("person ID", "components", "filters", "attribution"), "CJA data view design cross-channel"),
    _q("cja-s3", "Describe how identity stitching works in CJA and when you would configure it.", "identity", 4,
       ("person ID", "namespace", "stitching rules"), "CJA identity stitching"),
    _q("cja-s4", "What are the key steps to connect Adobe Analytics data to CJA?", "connections", 3,
       ("report suite", "mapping", "refresh"), "Adobe Analytics connection CJA"),
    _q("cja-s5", "How do filters and segments differ in CJA Analysis Workspace?", "workspace", 3,
       ("container", "scope", "breakdown"), "CJA filters segments"),
    _q("cja-s6", "When would you use guided analysis versus freeform in CJA?", "guided_analysis", 3,
       ("templates", "use cases", "ad hoc"), "CJA guided analysis"),
)

_CJA_ARCHITECT = (
    _q("cja-a1", "Design a CJA implementation for a retailer merging web, app, and call-center data.", "architecture", 5,
       ("connections", "identity", "data views", "governance"), "CJA multi-channel architecture"),
    _q("cja-a2", "What trade-offs exist between event-based and summary datasets in CJA?", "datasets", 4,
       ("latency", "granularity", "cost"), "CJA Experience Event summary datasets"),
    _q("cja-a3", "How would you govern metric definitions across multiple data views?", "governance", 4,
       ("calculated metrics", "naming", "approval"), "CJA metric governance"),
    _q("cja-a4", "Explain how attribution IQ settings affect cross-channel reporting.", "attribution", 4,
       ("lookback", "models", "participation"), "CJA Attribution IQ"),
    _q("cja-a5", "What considerations apply when migrating from Adobe Analytics to CJA?", "migration", 5,
       ("mapping", "variables", "training", "parallel run"), "Analytics to CJA migration"),
)

# ── AEP ───────────────────────────────────────────────────────────────────────

_AEP_JUNIOR = (
    _q("aep-j1", "What is XDM and why does Adobe Experience Platform use it?", "xdm", 2,
       ("schema", "standardization", "classes"), "XDM schema Experience Platform"),
    _q("aep-j2", "What is a dataset in AEP?", "datasets", 2,
       ("ingestion", "schema", "labels"), "AEP dataset create"),
    _q("aep-j3", "Name two identity-related concepts in AEP.", "identity", 2,
       ("identity namespace", "graph", "primary identity"), "AEP identity namespace"),
    _q("aep-j4", "What is Real-Time CDP?", "rtcdp", 2,
       ("profiles", "segments", "destinations"), "Real-Time CDP overview"),
    _q("aep-j5", "What is a segment definition in AEP?", "segmentation", 2,
       ("PQL", "audience", "batch streaming"), "AEP segment definition"),
)

_AEP_SENIOR = (
    _q("aep-s1", "Walk through creating an XDM schema for web behavioral events.", "xdm", 3,
       ("field groups", "mixins", "validation"), "XDM schema field groups"),
    _q("aep-s2", "Explain identity resolution and how the identity graph is built.", "identity", 4,
       ("namespaces", "algorithms", "person ID"), "AEP identity graph resolution"),
    _q("aep-s3", "Compare batch versus streaming ingestion in AEP.", "ingestion", 3,
       ("latency", "sources", "use cases"), "AEP batch streaming ingestion"),
    _q("aep-s4", "How do you build a segment for cart abandoners using streaming evaluation?", "segmentation", 4,
       ("streaming segmentation", "events", "profile"), "AEP streaming segmentation"),
    _q("aep-s5", "What are data usage labels and how do they affect activation?", "governance", 3,
       ("DULE", "consent", "destinations"), "AEP data usage labels governance"),
    _q("aep-s6", "Describe the role of destinations in RTCDP.", "destinations", 3,
       ("mapping", "identity", "activation"), "AEP destinations activation"),
)

_AEP_ARCHITECT = (
    _q("aep-a1", "Design an AEP data architecture for a global brand with regional consent requirements.", "architecture", 5,
       ("sandboxes", "labels", "workflows"), "AEP multi-region architecture governance"),
    _q("aep-a2", "How would you model identity for B2B versus B2C use cases in AEP?", "identity", 5,
       ("account", "person", "hierarchy"), "AEP B2B identity model"),
    _q("aep-a3", "What patterns exist for merging online and offline data in AEP?", "ingestion", 4,
       ("identity", "batch", "orchestration"), "AEP online offline merge"),
    _q("aep-a4", "Explain trade-offs between computed attributes and derived fields for profile enrichment.", "profiles", 4,
       ("latency", "maintenance", "PQL"), "AEP computed attributes profiles"),
    _q("aep-a5", "How do you ensure data quality and monitoring across AEP pipelines?", "operations", 4,
       ("observability", "DQ", "alerts"), "AEP data quality monitoring"),
)

# ── Web SDK ───────────────────────────────────────────────────────────────────

_WEB_SDK_SENIOR = (
    _q("ws-s1", "What is a datastream in Adobe Experience Platform Web SDK?", "datastreams", 3,
       ("edge", "configuration", "environment"), "Web SDK datastream configuration"),
    _q("ws-s2", "Compare the Web SDK (alloy.js) approach to legacy Adobe Analytics AppMeasurement.", "migration", 4,
       ("single library", "XDM", "edge"), "Web SDK vs AppMeasurement migration"),
    _q("ws-s3", "How do you send an XDM event using alloy.js?", "implementation", 3,
       ("sendEvent", "schema", "data layer"), "alloy sendEvent XDM"),
    _q("ws-s4", "Explain edge network versus direct server-side collection.", "edge", 3,
       ("latency", "first-party", "CDN"), "Experience Platform edge network"),
    _q("ws-s5", "What is the role of Adobe Tags (Launch) with Web SDK?", "tags", 3,
       ("extensions", "rules", "data elements"), "Tags Web SDK extension"),
)

_WEB_SDK_ARCHITECT = (
    _q("ws-a1", "Design a Web SDK rollout plan for a site still on Analytics and Target legacy tags.", "migration", 5,
       ("phased", "validation", "parallel"), "Web SDK migration plan"),
    _q("ws-a2", "How do you debug Web SDK implementations in the browser?", "debugging", 4,
       ("alloy log", "network", "validator"), "Web SDK debugging alloy"),
    _q("ws-a3", "What considerations apply to consent and privacy with edge collection?", "privacy", 4,
       ("consent", "opt-in", "IAB"), "Web SDK consent privacy"),
    _q("ws-a4", "How would you configure Web SDK for both AEP and Target from one datastream?", "configuration", 4,
       ("services", "mapping", "sandbox"), "datastream multiple services"),
    _q("ws-a5", "Explain how Web SDK handles identity sync across domains.", "identity", 4,
       ("ECID", "third-party cookies", "first-party ID"), "Web SDK identity ECID"),
)

# ── Target ────────────────────────────────────────────────────────────────────

_TARGET_SENIOR = (
    _q("tg-s1", "What is an mbox and how is it used in Adobe Target?", "mbox", 2,
       ("request", "offer", "location"), "Target mbox"),
    _q("tg-s2", "Describe the A/B test lifecycle in Target.", "ab_testing", 3,
       ("audience", "experiences", "metrics", "confidence"), "Target A/B test"),
    _q("tg-s3", "How do audiences in Target relate to AEP segments?", "audiences", 3,
       ("integration", "profile", "real-time"), "Target AEP audience integration"),
    _q("tg-s4", "What is the difference between auto-allocate and auto-target?", "automation", 3,
       ("multi-armed bandit", "personalization"), "Target auto allocate auto target"),
    _q("tg-s5", "When would you use Recommendations versus manual experience targeting?", "recommendations", 3,
       ("catalog", "criteria", "design"), "Target Recommendations"),
)

_TARGET_ARCHITECT = (
    _q("tg-a1", "Design a personalization architecture using Target, AEP, and Analytics.", "architecture", 5,
       ("data flow", "audiences", "reporting"), "Target AEP Analytics architecture"),
    _q("tg-a2", "How do you prevent flicker and manage implementation performance with Target?", "implementation", 4,
       ("at.js", "prehiding", "async"), "Target flicker prehiding"),
    _q("tg-a3", "Explain QA and preview workflows for Target activities.", "qa", 4,
       ("preview", "tokens", "staging"), "Target activity QA preview"),
    _q("tg-a4", "What governance model would you use for offer and audience ownership?", "governance", 4,
       ("RBAC", "workspace", "approval"), "Target governance workspaces"),
    _q("tg-a5", "Compare server-side delivery API versus client-side Target.", "delivery", 4,
       ("latency", "channels", "mobile"), "Target server-side delivery API"),
)

# ── AJO ───────────────────────────────────────────────────────────────────────

_AJO_JUNIOR = (
    _q("ajo-j1", "What is Adobe Journey Optimizer used for?", "overview", 2,
       ("journeys", "campaigns", "real-time"), "Adobe Journey Optimizer overview"),
    _q("ajo-j2", "What is the difference between a journey and a campaign in AJO?", "journeys", 2,
       ("event-triggered", "batch", "audience"), "AJO journeys vs campaigns"),
    _q("ajo-j3", "What is an action activity in an AJO journey?", "activities", 2,
       ("email", "push", "SMS", "channel"), "AJO action activity channel"),
    _q("ajo-j4", "What is a condition activity used for in a journey?", "activities", 2,
       ("branching", "audience qualification", "if-then"), "AJO condition activity"),
    _q("ajo-j5", "Name two channels AJO can send messages through.", "channels", 1,
       ("email", "push", "SMS", "in-app"), "AJO communication channels"),
)

_AJO_SENIOR = (
    _q("ajo-s1", "Walk through building an event-triggered journey from entry to exit.", "journeys", 3,
       ("entry event", "activities", "exit criteria"), "AJO event-triggered journey build"),
    _q("ajo-s2", "How do audiences and segments from AEP get used inside an AJO journey?", "audiences", 3,
       ("Real-Time CDP", "segment qualification", "entry audience"), "AJO AEP audience segment integration"),
    _q("ajo-s3", "Explain how the capping API prevents message fatigue.", "capping", 3,
       ("frequency rules", "suppression", "channel"), "AJO capping API frequency"),
    _q("ajo-s4", "What is the role of priority scores when journeys and campaigns compete for the same channel?", "priority", 3,
       ("arbitration", "conflict resolution", "scoring"), "AJO priority scores journeys campaigns"),
    _q("ajo-s5", "How do you build and test a personalized email using content templates?", "content", 3,
       ("templates", "personalization", "preview", "AI Assistant"), "AJO content templates personalization"),
    _q("ajo-s6", "Describe how you would set up an API-triggered campaign.", "campaigns", 3,
       ("API trigger", "high throughput", "transactional"), "AJO API-triggered campaigns"),
)

_AJO_ARCHITECT = (
    _q("ajo-a1", "Design a always-on journey architecture for onboarding across email, push, and SMS.", "architecture", 5,
       ("entry sources", "branching", "channel orchestration"), "AJO onboarding journey architecture"),
    _q("ajo-a2", "How would you architect approval workflows and governance for journeys and campaigns at scale?", "governance", 4,
       ("approve journeys", "roles", "access control"), "AJO approve journeys governance"),
    _q("ajo-a3", "Explain trade-offs between code-based experiences and the visual journey canvas.", "implementation", 4,
       ("code-based surface", "flexibility", "maintainability"), "AJO code-based experience canvas"),
    _q("ajo-a4", "How do you design a cross-channel arbitration strategy when a customer qualifies for multiple journeys at once?", "priority", 5,
       ("priority scores", "capping", "channel conflict"), "AJO cross-channel arbitration priority capping"),
    _q("ajo-a5", "What considerations apply when scaling high-throughput API-triggered campaigns for transactional use cases?", "operations", 4,
       ("throughput mode", "latency", "reliability"), "AJO high throughput API triggered campaigns"),
)

# ── Principal collections ─────────────────────────────────────────────────────

_CROSS_ARCH = (
    _q("pc-ca1", "Describe an end-to-end architecture from data collection through AEP, CJA, and activation.", "architecture", 5,
       ("Web SDK", "AEP", "CJA", "RTCDP", "Target"), "AEP CJA activation architecture"),
    _q("pc-ca2", "How would you rationalize metrics across Analytics, CJA, and AEP reporting?", "governance", 5,
       ("definitions", "single source of truth"), "cross-product metric governance"),
    _q("pc-ca3", "What are the key integration points between AEP and CJA for journey analysis?", "integration", 4,
       ("Experience Event", "connection", "data view"), "AEP CJA integration"),
    _q("pc-ca4", "How do you design sandbox and environment strategy for a multi-brand AEP+CJA rollout?", "operations", 5,
       ("dev staging prod", "sandboxes"), "AEP sandbox strategy"),
    _q("pc-ca5", "Explain how you would lead a workshop to align business and IT on a DXP roadmap.", "leadership", 4,
       ("stakeholders", "phases", "value"), "DXP roadmap workshop"),
)

_DATA_FOUNDATION = (
    _q("pc-df1", "Design an identity strategy spanning Web SDK, AEP, and CJA.", "identity", 5,
       ("ECID", "person ID", "stitching"), "identity strategy AEP CJA Web SDK"),
    _q("pc-df2", "How do you handle consent propagation from the web to AEP profiles and downstream activation?", "privacy", 5,
       ("consent", "labels", "destinations"), "consent AEP activation"),
    _q("pc-df3", "What schema design principles reduce rework across AEP and CJA?", "xdm", 4,
       ("field groups", "reuse", "governance"), "XDM schema design best practices"),
    _q("pc-df4", "Compare profile merge policies for household versus individual use cases.", "profiles", 5,
       ("merge policy", "graph", "priority"), "AEP profile merge policy"),
    _q("pc-df5", "How would you audit data lineage from source to segment to destination?", "governance", 4,
       ("catalog", "observability", "DQ"), "AEP data lineage audit"),
)

_PERSONALIZATION = (
    _q("pc-ps1", "Architect a real-time personalization stack using AEP, Target, and Journey Optimizer.", "architecture", 5,
       ("streaming", "edge", "journeys"), "personalization AEP Target AJO"),
    _q("pc-ps2", "When would you choose Target versus AJO for a campaign?", "strategy", 4,
       ("batch", "real-time", "orchestration"), "Target vs Journey Optimizer"),
    _q("pc-ps3", "How do computed attributes and streaming segments power same-session personalization?", "segmentation", 5,
       ("latency", "profile", "edge"), "streaming segmentation personalization"),
    _q("pc-ps4", "Design an experimentation framework that spans web, app, and email.", "experimentation", 4,
       ("A/B", "holdout", "reporting"), "cross-channel experimentation"),
    _q("pc-ps5", "What KPIs and guardrails would you establish for a personalization program?", "leadership", 4,
       ("ROI", "frequency caps", "brand safety"), "personalization program KPIs"),
)

def _load_scenario_bank() -> tuple[InterviewQuestion, ...]:
    path = Path(__file__).parent / "data" / "scenario_troubleshooting.json"
    with path.open() as f:
        rows = json.load(f)
    return tuple(
        _scenario_q(
            id=row["id"],
            question=row["question"],
            topic=row["topic"],
            difficulty=row["difficulty"],
            hint=row["retrieval_hint"],
            rubric=row["grading_rubric"],
        )
        for row in rows
    )


_SCENARIO_TROUBLESHOOTING = _load_scenario_bank()

# Seed bank — the canonical source is now the `interview_questions` table in
# Postgres (see backend/core/google_db.py). These tuples are only used to seed
# that table on startup (idempotent — see seed_all_questions below); runtime
# question lookups (get_question_set, validate_profile, get_profiles_payload)
# query the database, not this dict.
_SEED_BANK: dict[tuple[str, str], tuple[InterviewQuestion, ...]] = {
    ("junior", "cja"): _CJA_JUNIOR,
    ("senior", "cja"): _CJA_SENIOR,
    ("architect", "cja"): _CJA_ARCHITECT,
    ("junior", "aep"): _AEP_JUNIOR,
    ("senior", "aep"): _AEP_SENIOR,
    ("architect", "aep"): _AEP_ARCHITECT,
    ("senior", "web_sdk"): _WEB_SDK_SENIOR,
    ("architect", "web_sdk"): _WEB_SDK_ARCHITECT,
    ("senior", "target"): _TARGET_SENIOR,
    ("architect", "target"): _TARGET_ARCHITECT,
    ("junior", "ajo"): _AJO_JUNIOR,
    ("senior", "ajo"): _AJO_SENIOR,
    ("architect", "ajo"): _AJO_ARCHITECT,
    ("principal", "cross_solution_architecture"): _CROSS_ARCH,
    ("principal", "data_foundation"): _DATA_FOUNDATION,
    ("principal", "personalization_stack"): _PERSONALIZATION,
    ("multi", "scenario_troubleshooting"): _SCENARIO_TROUBLESHOOTING,
}

_VALID_LEVELS = {l["id"] for l in LEVELS}
_VALID_SOLUTIONS = {s["id"] for s in SOLUTIONS}
_VALID_COLLECTIONS = {c["id"] for c in COLLECTIONS}
_SINGLE_SOLUTION_IDS = _VALID_SOLUTIONS - {"all"}
_SINGLE_COLLECTION_IDS = _VALID_COLLECTIONS - {"all"}


def seed_all_questions() -> None:
    """Insert every seed question into interview_questions (version 1) if it isn't
    already there. Idempotent — safe to call on every startup."""
    from backend.core import google_db

    for (level, profile_id), bank in _SEED_BANK.items():
        for q in bank:
            google_db.seed_interview_question(
                question_id=q.id,
                level=level,
                profile_id=profile_id,
                topic=q.topic,
                difficulty=q.difficulty,
                prompt_text=q.question,
                expected_themes=list(q.expected_themes),
                retrieval_hint=q.retrieval_hint,
                question_type=q.question_type,
                grading_rubric=q.grading_rubric,
            )


def _row_to_question(row: dict) -> InterviewQuestion:
    return InterviewQuestion(
        id=row["question_id"],
        question=row["prompt_text"],
        topic=row["topic"],
        difficulty=row["difficulty"],
        expected_themes=tuple(row["expected_themes"]),
        retrieval_hint=row["retrieval_hint"],
        version=row["version"],
        question_type=row.get("question_type", "standard"),
        grading_rubric=row.get("grading_rubric"),
    )


def _pick(
    pool: list[InterviewQuestion],
    n: int,
    *,
    exclude_ids: set[str],
) -> list[InterviewQuestion]:
    """Randomly sample up to n questions from pool, preferring ones not in
    exclude_ids (recently asked). Falls back to the full pool if excluding
    would leave too few to satisfy n."""
    preferred = [q for q in pool if q.id not in exclude_ids]
    candidates = preferred if len(preferred) >= n else pool
    return random.sample(candidates, min(n, len(candidates)))


def _merge_bank_lists(
    banks: list[list[InterviewQuestion]],
    *,
    per_bank: int,
    max_total: int,
    exclude_ids: set[str],
) -> list[InterviewQuestion]:
    merged: list[InterviewQuestion] = []
    order = list(range(len(banks)))
    random.shuffle(order)
    for i in order:
        merged.extend(_pick(banks[i], per_bank, exclude_ids=exclude_ids))
        if len(merged) >= max_total:
            break
    random.shuffle(merged)
    return merged[:max_total]


def _fetch_bank(level: str, profile_id: str, user_id: str = "") -> list[InterviewQuestion]:
    from backend.core import google_db

    if profile_id == "all":
        exclude_ids = google_db.get_recent_question_ids(user_id, level, profile_id)
        if level == "principal":
            ids = list(_SINGLE_COLLECTION_IDS)
            per_bank = 2
        else:
            ids = list(_SINGLE_SOLUTION_IDS)
            per_bank = 2
        banks: list[list[InterviewQuestion]] = []
        for pid in ids:
            rows = google_db.get_active_question_bank(level, pid)
            if rows:
                banks.append([_row_to_question(r) for r in rows])
        if level in _SCENARIO_FOLDED_LEVELS:
            rows = google_db.get_active_question_bank(level, "scenario_troubleshooting")
            if rows:
                banks.append([_row_to_question(r) for r in rows])
        if level != "principal" and len(banks) <= 2:
            per_bank = 3
        return _merge_bank_lists(banks, per_bank=per_bank, max_total=8, exclude_ids=exclude_ids)

    rows = google_db.get_active_question_bank(level, profile_id)
    pool = [_row_to_question(r) for r in rows]
    random.shuffle(pool)
    return pool


def get_profiles_payload() -> dict:
    from backend.core import google_db

    combinations = []
    for level, profile_id in google_db.list_active_question_combinations():
        if level == "multi":
            # Stored once, not tied to a single level — expand into every level
            # that collection actually declares (see COLLECTIONS[...]["levels"]).
            for real_level in _collection_levels(profile_id):
                combinations.append({"level": real_level, "profile_id": profile_id})
        else:
            combinations.append({"level": level, "profile_id": profile_id})
    for level in ("junior", "senior", "architect"):
        combinations.append({"level": level, "profile_id": "all"})
    combinations.append({"level": "principal", "profile_id": "all"})
    return {
        "levels": list(LEVELS),
        "solutions": list(SOLUTIONS),
        "collections": list(COLLECTIONS),
        "combinations": combinations,
    }


def _collection_levels(profile_id: str) -> tuple[str, ...]:
    for c in COLLECTIONS:
        if c["id"] == profile_id:
            return c["levels"]
    return ()


def validate_profile(level: str, profile_id: str) -> str | None:
    """Return error message if invalid, else None."""
    if level not in _VALID_LEVELS:
        return f"Unknown level: {level}"
    if profile_id in _VALID_COLLECTIONS:
        if level not in _collection_levels(profile_id):
            return f"Collection {profile_id} is not available at level {level}"
    elif profile_id not in _VALID_SOLUTIONS:
        return f"Unknown solution: {profile_id}"
    if not _fetch_bank(level, profile_id):
        return f"No question bank for {level} × {profile_id}"
    return None


def get_question_set(level: str, profile_id: str, user_id: str = "") -> list[InterviewQuestion]:
    err = validate_profile(level, profile_id)
    if err:
        raise ValueError(err)
    return _fetch_bank(level, profile_id, user_id)


def profile_label(level: str, profile_id: str) -> str:
    if profile_id == "all":
        return "All collections" if level == "principal" else "All solutions"
    for c in COLLECTIONS:
        if c["id"] == profile_id:
            return c["label"]
    for s in SOLUTIONS:
        if s["id"] == profile_id:
            return s["label"]
    return profile_id
