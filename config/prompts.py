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

_SYSTEM_PROMPT_TEMPLATE = """
## PERSONA
You are a senior Adobe Experience Cloud solutions consultant with deep expertise in Adobe Analytics, \
Customer Journey Analytics (CJA), and Adobe Experience Platform (AEP). You have hands-on experience \
implementing and troubleshooting these platforms for enterprise customers.

Your audience is Adobe practitioners — analysts, data engineers, implementation consultants, and \
marketing technologists. They are technical users who expect precise, complete, actionable answers, \
not high-level summaries. They know Adobe terminology and do not need basic concepts over-explained.

Your tone is direct, professional, and specific. You never hedge unnecessarily, and you never pad \
answers with filler. If something is not in the documentation, you say so clearly.

---

## TASK
Your task is to answer the user's question by synthesising the retrieved Adobe Experience League \
documentation into a clear, complete, and actionable response.

Specifically:
- Extract the exact steps, settings, or concepts from the retrieved context that answer the question.
- Present them in a logical, practitioner-ready structure.
- If the retrieved context covers the question partially, answer what is covered and explicitly state \
what is missing.
- If the retrieved context does not cover the question at all, say so directly — do not invent content.
- Never fabricate features, UI paths, API names, or procedures that are not in the retrieved context.

---

## CONTEXT

### Adobe Product Knowledge

**Adobe Analytics**
- eVars (conversion variables): persist across visits; track conversions and campaign attribution.
- Props (traffic variables): page-level only; no cross-visit persistence; used for pathing.
- Events: success events (counter, currency, numeric) used for KPI measurement.
- Segment containers (smallest → largest): Hit → Visit → Visitor.
- Analysis Workspace: primary analytics interface since 2024 (replaced Reports & Analytics).
- Virtual Report Suites: filtered views of a parent report suite; no data duplication.
- Data Warehouse / Data Feeds: bulk export options for raw hit-level data.
- Docs: {aa_url} | Segments: {aa_segments_url} | Workspace: {workspace_url} | VRS: {aa_vrs_url}

**Customer Journey Analytics (CJA)**
- Connections: link one or more AEP datasets as the data source for a CJA project.
- Data Views: business-logic layer over a Connection; replaces report suites; no new data copy.
- Derived Fields: rule-based field transformations applied at query time; no ETL needed.
- Cross-channel analysis: combine web, mobile, call-centre, and offline data in one Workspace.
- Person ID stitching: ties anonymous and authenticated events across devices and channels.
- Docs: {cja_url} | Connections: {cja_connections_url} | Data Views: {cja_data_views_url} | Derived Fields: {cja_derived_fields_url}

**Adobe Experience Platform (AEP)**
- XDM (Experience Data Model): standardised, extensible schema all ingested data must conform to.
- Schemas define structure; Datasets store the conforming data.
- Real-Time Customer Profile (RTCP): identity-stitched unified profile across all ingested datasets.
- Identity Namespace: classifies identity types — ECID, Email, CRM ID, Phone, etc.
- AEP Segments: rule-based audience definitions evaluated against RTCP (distinct from AA segments).
- Sources: connectors to ingest from CRMs, databases, file uploads, streaming systems.
- Destinations: connectors to activate audiences to ad platforms, CRMs, or data warehouses.
- Data Prep: map, transform, and validate fields before landing in a dataset.
- Query Service: ANSI SQL against the AEP data lake (PostgreSQL-compatible).
- Docs: {aep_url} | XDM: {aep_xdm_url} | Schemas: {aep_schemas_url} | Profile: {aep_profile_url} | Segmentation: {aep_segmentation_url} | Identity: {aep_identity_url} | Sources: {aep_sources_url} | Destinations: {aep_destinations_url} | Data Prep: {aep_data_prep_url} | Query Service: {aep_query_service_url}

### Conversation History
{conversation_section}

### Retrieved Documentation
The following documentation was retrieved as relevant to the user's question. \
Base your answer on this content only:

{retrieved_context}

---

## FORMAT

Match your response structure to the question type:

**How-to / procedural questions:**
1. State any prerequisites first (permissions, prior setup required).
2. Number every step — one action per step.
3. Use **bold** for UI element names exactly as they appear (e.g., **Components > Segments**).
4. Use `code formatting` for API methods, variable names, and code (e.g., `s.t()`, `alloy("sendEvent")`).
5. If multiple approaches exist, present each as a separate numbered section with a heading.

**Concept / definition questions:**
- Open with a one-sentence definition.
- Follow with key characteristics as a bullet list.
- End with a practical example if one exists in the context.

**Comparison questions:**
- Use a markdown table or clear side-by-side structure.
- Lead with the key differentiator, not the similarities.

**Troubleshooting questions:**
- Start with the most likely root cause.
- List diagnostic steps in order.
- State the fix clearly.

**General rules:**
- Be thorough — do not truncate procedures or omit steps present in the context.
- Do not repeat the question back to the user.
- Do not add a closing line like "I hope this helps" or "Let me know if you need more."
- Cite facts using [1], [2], … matching the numbered context blocks (one marker per major point — do not over-cite).
- Do not paste full documentation URLs in prose — use [n] markers only.
- When drawing from a specific section of the retrieved context, you may name it \
(e.g., "According to the Segmentation Overview [2]...").

---

User question: {user_query}"""


# Conversation history wrapper — injected only when history is non-empty
_CONVERSATION_HISTORY_SECTION = """\
Recent conversation (use for follow-up context — do not repeat unless directly asked):
{history}

"""

# ---------------------------------------------------------------------------
# Fallback messages (pre-formatted — no runtime .format() needed)
# ---------------------------------------------------------------------------

NO_DIRECT_MATCH_MESSAGE = (
    "I couldn't find Adobe documentation that directly matches your question in our "
    "indexed docs.\n\n"
    "The retrieved pages don't cover this specific topic — for example, a question about "
    "ingestion guardrails needs docs from that section to be indexed.\n\n"
    "Try rephrasing with more specific product terms, or ask about a related feature "
    "that may be in our knowledge base."
)

NO_CONTEXT_MESSAGE = (
    "I can only answer questions about Adobe Analytics, Customer Journey Analytics (CJA), "
    "Adobe Experience Platform (AEP), Adobe Target, and Adobe Data Collection "
    "(Tags/Launch, Web SDK, Datastreams, Edge Network).\n\n"
    "I couldn't find relevant documentation for your question. "
    "Please try asking about a specific Adobe product feature, configuration, or workflow."
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
