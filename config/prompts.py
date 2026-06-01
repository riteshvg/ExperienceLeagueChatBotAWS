"""
System prompts for Adobe Analytics RAG Chatbot.

Responsibilities:
- Canonical Experience League URLs for all supported products
- Anti-hallucination grounding rules
- Citation and response format instructions
- Conversation history formatting for multi-turn context
"""

from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Canonical Experience League URLs
# ---------------------------------------------------------------------------

PRODUCT_URLS: Dict[str, str] = {
    # Product homes
    "adobe_analytics":          "https://experienceleague.adobe.com/docs/analytics/",
    "cja":                      "https://experienceleague.adobe.com/docs/analytics-platform/",
    "aep":                      "https://experienceleague.adobe.com/docs/experience-platform/",
    # Adobe Analytics sections
    "workspace":                "https://experienceleague.adobe.com/docs/analytics/analyze/analysis-workspace/home.html",
    "aa_segments":              "https://experienceleague.adobe.com/docs/analytics/components/segmentation/seg-home.html",
    "aa_calculated_metrics":    "https://experienceleague.adobe.com/docs/analytics/components/calculated-metrics/calcmetric-workflow/cm-build-metrics.html",
    "aa_virtual_report_suites": "https://experienceleague.adobe.com/docs/analytics/components/virtual-report-suites/vrs-about.html",
    "aa_data_warehouse":        "https://experienceleague.adobe.com/docs/analytics/export/data-warehouse/data-warehouse.html",
    "aa_data_feeds":            "https://experienceleague.adobe.com/docs/analytics/export/analytics-data-feed/data-feed-overview.html",
    # CJA sections
    "cja_connections":          "https://experienceleague.adobe.com/docs/analytics-platform/using/cja-connections/overview.html",
    "cja_data_views":           "https://experienceleague.adobe.com/docs/analytics-platform/using/cja-dataviews/data-views.html",
    "cja_workspace":            "https://experienceleague.adobe.com/docs/analytics-platform/using/cja-workspace/home.html",
    "cja_derived_fields":       "https://experienceleague.adobe.com/docs/analytics-platform/using/cja-dataviews/derived-fields/derived-fields.html",
    # AEP sections
    "aep_xdm":                  "https://experienceleague.adobe.com/docs/experience-platform/xdm/home.html",
    "aep_schemas":              "https://experienceleague.adobe.com/docs/experience-platform/xdm/schema/composition.html",
    "aep_profile":              "https://experienceleague.adobe.com/docs/experience-platform/profile/home.html",
    "aep_segmentation":         "https://experienceleague.adobe.com/docs/experience-platform/segmentation/home.html",
    "aep_sources":              "https://experienceleague.adobe.com/docs/experience-platform/sources/home.html",
    "aep_destinations":         "https://experienceleague.adobe.com/docs/experience-platform/destinations/home.html",
    "aep_data_prep":            "https://experienceleague.adobe.com/docs/experience-platform/data-prep/home.html",
    "aep_query_service":        "https://experienceleague.adobe.com/docs/experience-platform/query/home.html",
    "aep_identity":             "https://experienceleague.adobe.com/docs/experience-platform/identity/home.html",
}

# ---------------------------------------------------------------------------
# System prompt template
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT_TEMPLATE = """You are an expert assistant for Adobe Experience League documentation, \
specializing in Adobe Analytics, Customer Journey Analytics (CJA), and Adobe Experience Platform (AEP).

CRITICAL RULES:
1. Answer ONLY using the provided documentation context below.
2. If the context does not contain the answer, say: "I don't have complete information about this \
in the documentation. The available context covers [what you found], but doesn't include [what's missing]."
3. For multi-step processes, include ALL steps in sequential order.
4. When referencing UI elements, use exact names from documentation (e.g., "Components > Segments").
5. Preserve technical terms exactly: eVar, prop, s.t(), s.tl(), Workspace, XDM, RTCP, ECID.
6. If prerequisites exist, mention them FIRST before main steps.
7. Never invent features, settings, or procedures not in the context.
8. If multiple approaches exist in the context, present all options.

CITATION RULES:
- When your answer draws from a specific section of the retrieved context, name that section \
(e.g., "As described in the Data Views documentation..." or "According to the Segments guide...").
- Use only section or page titles that are visible in the retrieved context — do not invent names.
- Do not embed raw URLs in your prose; verified source links are appended below your response automatically.

RESPONSE FORMAT:
- How-to / setup questions: numbered steps, one per line.
- Concept definitions: one-sentence definition first, then elaboration.
- Comparisons: side-by-side structure or a short table.
- Keep responses under 400 words unless the procedure genuinely requires more detail.
- Use **bold** for UI element names and `code formatting` for function or API names \
(e.g., `s.t()`, `s.tl()`, `retrieveAndGenerate`).
- Use bullet points for unordered lists; use numbered lists only for sequential steps.

--- PRODUCT REFERENCE ---

Adobe Analytics:
- eVars (conversion variables): persist across visits, used to track conversions.
- Props (traffic variables): page-level only, no cross-visit persistence.
- Events: success events, counter events, currency events.
- Segment containers (smallest → largest): Hit (page view) → Visit (session) → Visitor (person).
- Analysis Workspace: current analytics interface, replaced Reports & Analytics in 2024.
- Virtual Report Suites: filtered views of a parent report suite, no data duplication.
- Data Warehouse / Data Feeds: bulk export options for raw hit-level data.
- Documentation home: {aa_url}
- Segments guide: {aa_segments_url}
- Workspace guide: {workspace_url}
- Virtual Report Suites: {aa_vrs_url}

Customer Journey Analytics (CJA):
- Connections: link one or more AEP datasets as the data source for a CJA project.
- Data Views: business-logic layer over a Connection — replaces report suites, no new data copy.
- Derived Fields: rule-based field transformations applied at query time, no ETL pipeline needed.
- Cross-channel analysis: combine web, mobile, call-centre, and offline data in one Workspace.
- Person ID stitching: ties anonymous and authenticated events across devices and channels.
- Documentation home: {cja_url}
- Connections: {cja_connections_url}
- Data Views: {cja_data_views_url}
- Derived Fields: {cja_derived_fields_url}

Adobe Experience Platform (AEP):
- XDM (Experience Data Model): standardised, extensible schemas all data must conform to.
- Schemas: define the structure; Datasets: store the data conforming to a schema.
- Real-Time Customer Profile (RTCP): identity-stitched unified profile built from all ingested datasets.
- Identity Namespace: labels that classify identity types — ECID, Email, CRM ID, Phone, etc.
- Segments (AEP): rule-based audience definitions evaluated against RTCP, distinct from AA segments.
- Sources: connectors to ingest data from external systems (CRM, databases, file uploads, streaming).
- Destinations: connectors to activate audiences to external ad platforms, CRMs, or data warehouses.
- Data Prep: map, transform, and validate fields before they land in a dataset.
- Query Service: run ANSI SQL directly against the AEP data lake (PostgreSQL-compatible endpoint).
- Documentation home: {aep_url}
- XDM overview: {aep_xdm_url}
- Schema composition: {aep_schemas_url}
- Real-Time Customer Profile: {aep_profile_url}
- Segmentation: {aep_segmentation_url}
- Identity Service: {aep_identity_url}
- Sources: {aep_sources_url}
- Destinations: {aep_destinations_url}
- Data Prep: {aep_data_prep_url}
- Query Service: {aep_query_service_url}

--- CONTEXT ---
{conversation_section}Retrieved documentation:
{retrieved_context}

User question: {user_query}

Remember: Base your answer solely on the retrieved documentation above. \
State explicitly what is covered and what is missing if the context is incomplete."""


# Conversation history wrapper — injected only when history is non-empty
_CONVERSATION_HISTORY_SECTION = """\
Recent conversation (use for follow-up context — do not repeat unless directly asked):
{history}

"""

# ---------------------------------------------------------------------------
# Fallback messages (pre-formatted — no runtime .format() needed)
# ---------------------------------------------------------------------------

NO_CONTEXT_MESSAGE = (
    "I don't have any relevant documentation to answer your question.\n\n"
    "This could mean:\n"
    "1. The documentation doesn't cover this topic\n"
    "2. The knowledge base search didn't find relevant content\n"
    "3. The question is outside the scope of Adobe Analytics, CJA, or AEP documentation\n\n"
    "Please try:\n"
    "- Rephrasing with more specific terms\n"
    "- Using Adobe-specific terminology (eVar, prop, segment, XDM, data view, RTCP, etc.)\n"
    "- Breaking a complex question into smaller parts\n\n"
    "Documentation home pages:\n"
    f"- Adobe Analytics: {PRODUCT_URLS['adobe_analytics']}\n"
    f"- Customer Journey Analytics: {PRODUCT_URLS['cja']}\n"
    f"- Adobe Experience Platform: {PRODUCT_URLS['aep']}"
)

INCOMPLETE_CONTEXT_TEMPLATE = """\
I found some information about this topic, but the documentation appears incomplete.

What I found:
{found_info}

What's missing:
{missing_info}

Please try:
- Being more specific about which aspect you need help with
- Using different keywords or terminology
- Breaking your question into smaller parts"""


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def build_conversation_history(
    chat_history: List[Dict],
    max_turns: int = 3,
    max_chars: int = 1500,
) -> str:
    """
    Build a compact conversation history string from the most recent chat turns.

    Only complete user → assistant pairs are included; any trailing solo user
    message (the current in-progress query) is intentionally excluded.
    """
    if not chat_history or len(chat_history) < 2:
        return ""

    # Collect complete pairs in order
    pairs: List[tuple] = []
    i = 0
    while i < len(chat_history) - 1:
        if chat_history[i]["role"] == "user" and chat_history[i + 1]["role"] == "assistant":
            pairs.append((chat_history[i]["content"], chat_history[i + 1]["content"]))
            i += 2
        else:
            i += 1

    if not pairs:
        return ""

    recent = pairs[-max_turns:]
    history_parts: List[str] = []
    total = 0

    for user_msg, assistant_msg in recent:
        user_snippet = user_msg[:200] + "..." if len(user_msg) > 200 else user_msg
        # Strip appended citations block before including in history
        assistant_text = assistant_msg.split("\n\n---\n\n### 📚 Sources")[0]
        assistant_snippet = assistant_text[:300] + "..." if len(assistant_text) > 300 else assistant_text

        entry = f"User: {user_snippet}\nAssistant: {assistant_snippet}"
        if total + len(entry) > max_chars:
            break
        history_parts.append(entry)
        total += len(entry)

    return "\n\n".join(history_parts)


def format_system_prompt(
    retrieved_context: str,
    user_query: str,
    conversation_history: str = "",
) -> str:
    """
    Render the system prompt with retrieved documentation, user query, and
    optional prior conversation turns.
    """
    if not retrieved_context or not retrieved_context.strip():
        return NO_CONTEXT_MESSAGE

    conversation_section = ""
    if conversation_history:
        conversation_section = _CONVERSATION_HISTORY_SECTION.format(history=conversation_history)

    return _SYSTEM_PROMPT_TEMPLATE.format(
        # Adobe Analytics URLs
        aa_url=PRODUCT_URLS["adobe_analytics"],
        aa_segments_url=PRODUCT_URLS["aa_segments"],
        workspace_url=PRODUCT_URLS["workspace"],
        aa_vrs_url=PRODUCT_URLS["aa_virtual_report_suites"],
        # CJA URLs
        cja_url=PRODUCT_URLS["cja"],
        cja_connections_url=PRODUCT_URLS["cja_connections"],
        cja_data_views_url=PRODUCT_URLS["cja_data_views"],
        cja_derived_fields_url=PRODUCT_URLS["cja_derived_fields"],
        # AEP URLs
        aep_url=PRODUCT_URLS["aep"],
        aep_xdm_url=PRODUCT_URLS["aep_xdm"],
        aep_schemas_url=PRODUCT_URLS["aep_schemas"],
        aep_profile_url=PRODUCT_URLS["aep_profile"],
        aep_segmentation_url=PRODUCT_URLS["aep_segmentation"],
        aep_identity_url=PRODUCT_URLS["aep_identity"],
        aep_sources_url=PRODUCT_URLS["aep_sources"],
        aep_destinations_url=PRODUCT_URLS["aep_destinations"],
        aep_data_prep_url=PRODUCT_URLS["aep_data_prep"],
        aep_query_service_url=PRODUCT_URLS["aep_query_service"],
        # Dynamic content
        conversation_section=conversation_section,
        retrieved_context=retrieved_context,
        user_query=user_query,
    )


def format_incomplete_context_message(found_info: str, missing_info: str) -> str:
    return INCOMPLETE_CONTEXT_TEMPLATE.format(
        found_info=found_info,
        missing_info=missing_info,
    )


def validate_context_quality(retrieved_context: str) -> Dict:
    if not retrieved_context:
        return {
            "valid": False,
            "reason": "Empty context",
            "suggestion": "Try different keywords or rephrase the question",
        }
    if len(retrieved_context) < 100:
        return {
            "valid": False,
            "reason": "Context too short",
            "suggestion": "Context may be incomplete — try more specific terms",
        }
    return {
        "valid": True,
        "reason": "Context looks good",
        "context_length": len(retrieved_context),
    }


def should_use_fallback(retrieved_context: str, min_context_length: int = 100) -> bool:
    if not retrieved_context:
        return True
    return len(retrieved_context.strip()) < min_context_length


# Quick reference for common Adobe Analytics terms (used by debug / admin views)
ADOBE_TERMINOLOGY: Dict[str, str] = {
    "eVar":             "Conversion variable (persists across visits)",
    "prop":             "Traffic variable (page-level only)",
    "s.t()":            "Page view beacon (s.track)",
    "s.tl()":           "Link tracking beacon (s.trackLink)",
    "Workspace":        "Modern analytics interface (replaced Reports & Analytics in 2024)",
    "Segment":          "Filtered subset of data",
    "Calculated Metric": "Custom metric derived from existing metrics",
    "Virtual Report Suite": "Filtered view of a parent report suite",
    "Data View":        "CJA equivalent of a report suite — business logic over a Connection",
    "Connection":       "CJA data source — links AEP datasets to a project",
    "Derived Field":    "CJA field transformation applied at query time",
    "XDM":              "Experience Data Model — standardised schema format for AEP",
    "RTCP":             "Real-Time Customer Profile — unified identity-stitched profile in AEP",
    "ECID":             "Experience Cloud ID — Adobe's cross-device identity namespace",
}


def get_adobe_term_definition(term: str) -> str:
    return ADOBE_TERMINOLOGY.get(term, ADOBE_TERMINOLOGY.get(term.lower(), ""))
