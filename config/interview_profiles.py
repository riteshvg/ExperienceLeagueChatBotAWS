"""
Interview prep question banks for Interviewer Mode.

Levels × solutions (or Principal collections) with topic metadata for retrieval.
"""

from __future__ import annotations

from dataclasses import dataclass
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
        "description": "Mixed questions across CJA, AEP, Web SDK, and Target",
    },
    {"id": "cja", "label": "Customer Journey Analytics", "short": "CJA"},
    {"id": "aep", "label": "Adobe Experience Platform", "short": "AEP"},
    {"id": "web_sdk", "label": "Web SDK / Data Collection", "short": "Web SDK"},
    {"id": "target", "label": "Adobe Target", "short": "Target"},
)

# Principal-only multi-solution collections
COLLECTIONS: tuple[dict[str, str], ...] = (
    {
        "id": "all",
        "label": "All collections",
        "description": "Mixed questions from every Principal cross-solution track",
    },
    {
        "id": "cross_solution_architecture",
        "label": "Cross-Solution Architecture",
        "description": "AEP → CJA → Activation data flows and governance",
    },
    {
        "id": "data_foundation",
        "label": "Data Foundation & Identity",
        "description": "Schemas, identity graphs, and stitching across products",
    },
    {
        "id": "personalization_stack",
        "label": "Personalization Stack",
        "description": "Target, AJO, and Real-Time CDP activation patterns",
    },
)


@dataclass(frozen=True)
class InterviewQuestion:
    id: str
    question: str
    topic: str
    difficulty: int
    expected_themes: tuple[str, ...]
    retrieval_hint: str


def _q(
    id: str,
    question: str,
    topic: str,
    difficulty: int,
    themes: tuple[str, ...],
    hint: str,
) -> InterviewQuestion:
    return InterviewQuestion(id, question, topic, difficulty, themes, hint)


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

_SINGLE_BANK: dict[tuple[str, str], tuple[InterviewQuestion, ...]] = {
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
    ("principal", "cross_solution_architecture"): _CROSS_ARCH,
    ("principal", "data_foundation"): _DATA_FOUNDATION,
    ("principal", "personalization_stack"): _PERSONALIZATION,
}

_VALID_LEVELS = {l["id"] for l in LEVELS}
_VALID_SOLUTIONS = {s["id"] for s in SOLUTIONS}
_VALID_COLLECTIONS = {c["id"] for c in COLLECTIONS}
_SINGLE_SOLUTION_IDS = _VALID_SOLUTIONS - {"all"}
_SINGLE_COLLECTION_IDS = _VALID_COLLECTIONS - {"all"}


def _merge_banks(
    keys: list[tuple[str, str]],
    *,
    per_bank: int = 2,
    max_total: int = 8,
) -> tuple[InterviewQuestion, ...]:
    merged: list[InterviewQuestion] = []
    for key in keys:
        bank = _SINGLE_BANK.get(key)
        if not bank:
            continue
        merged.extend(bank[:per_bank])
        if len(merged) >= max_total:
            break
    return tuple(merged[:max_total])


def _all_solutions_bank(level: str) -> tuple[InterviewQuestion, ...]:
    keys = [(level, sid) for sid in _SINGLE_SOLUTION_IDS if (level, sid) in _SINGLE_BANK]
    per_bank = 2 if len(keys) > 2 else 3
    return _merge_banks(keys, per_bank=per_bank, max_total=8)


def _all_collections_bank() -> tuple[InterviewQuestion, ...]:
    keys = [("principal", cid) for cid in _SINGLE_COLLECTION_IDS]
    return _merge_banks(keys, per_bank=2, max_total=8)


QUESTION_BANK: dict[tuple[str, str], tuple[InterviewQuestion, ...]] = {
    **_SINGLE_BANK,
    ("junior", "all"): _all_solutions_bank("junior"),
    ("senior", "all"): _all_solutions_bank("senior"),
    ("architect", "all"): _all_solutions_bank("architect"),
    ("principal", "all"): _all_collections_bank(),
}


def get_profiles_payload() -> dict:
    combinations = [
        {"level": level, "profile_id": profile_id}
        for (level, profile_id) in QUESTION_BANK.keys()
    ]
    return {
        "levels": list(LEVELS),
        "solutions": list(SOLUTIONS),
        "collections": list(COLLECTIONS),
        "combinations": combinations,
    }


def validate_profile(level: str, profile_id: str) -> str | None:
    """Return error message if invalid, else None."""
    if level not in _VALID_LEVELS:
        return f"Unknown level: {level}"
    if level == "principal":
        if profile_id not in _VALID_COLLECTIONS:
            return f"Unknown collection for principal level: {profile_id}"
    elif profile_id not in _VALID_SOLUTIONS:
        return f"Unknown solution: {profile_id}"
    key = (level, profile_id)
    if key not in QUESTION_BANK or not QUESTION_BANK[key]:
        return f"No question bank for {level} × {profile_id}"
    return None


def get_question_set(level: str, profile_id: str) -> list[InterviewQuestion]:
    err = validate_profile(level, profile_id)
    if err:
        raise ValueError(err)
    return list(QUESTION_BANK[(level, profile_id)])


def profile_label(level: str, profile_id: str) -> str:
    if profile_id == "all":
        return "All collections" if level == "principal" else "All solutions"
    if level == "principal":
        for c in COLLECTIONS:
            if c["id"] == profile_id:
                return c["label"]
        return profile_id
    for s in SOLUTIONS:
        if s["id"] == profile_id:
            return s["label"]
    return profile_id
