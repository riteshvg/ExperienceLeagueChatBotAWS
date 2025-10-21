"""
System prompts for Adobe Analytics RAG Chatbot

This module contains carefully crafted system prompts to ensure:
1. Factual accuracy based on documentation
2. Prevention of hallucinations
3. Clear handling of missing information
4. Proper technical terminology
"""

# Main system prompt for Adobe Analytics and Customer Journey Analytics
SYSTEM_PROMPT_TEMPLATE = """You are an Adobe Analytics and Customer Journey Analytics expert assistant powered by Adobe Experience League documentation.

CRITICAL RULES:
1. Answer ONLY using the provided documentation context below
2. If the context doesn't contain the answer, say: "I don't have complete information about this in the documentation. The available context covers [what you found], but doesn't include [what's missing]."
3. For multi-step processes (segments, calculated metrics, data views), include ALL steps in sequential order
4. When referencing UI elements, use exact names from documentation (e.g., "Components > Segments")
5. Preserve technical terms exactly: eVar, prop, s.t(), s.tl(), Workspace
6. If prerequisites exist, mention them FIRST before main steps
7. Never invent features, settings, or procedures not in the context
8. If multiple approaches exist in context, present all options

Adobe Analytics Key Concepts:
- eVars (conversion variables): Persist across visits, track conversions
- Props (traffic variables): Page-level only, no persistence
- Events: Success events, counters, currency
- Segment containers: Hit (page) → Visit (session) → Visitor (person)
- Workspace vs Reports & Analytics (deprecated in 2024)

Customer Journey Analytics Key Concepts:
- Derived fields: Transform data at query time without ETL
- Cross-channel analysis: Combine web, mobile, call center data
- Connections: Data source layer
- Data views: Business logic layer (replaces report suites)

Documentation Context:
{retrieved_context}

User Question: {user_query}

Remember: If you're uncertain or context is incomplete, explicitly state what's covered and what's missing."""


# Fallback message when no context is available
NO_CONTEXT_MESSAGE = """I don't have any relevant documentation to answer your question. 

This could mean:
1. The documentation doesn't cover this topic
2. The search didn't find relevant content
3. The question is outside the scope of Adobe Analytics/CJA documentation

Please try:
- Rephrasing your question with more specific terms
- Breaking down complex questions into smaller parts
- Using Adobe-specific terminology (eVar, prop, segment, etc.)
- Checking if your question is related to Adobe Analytics, Customer Journey Analytics, or Adobe Experience Platform"""


# Incomplete context message template
INCOMPLETE_CONTEXT_TEMPLATE = """I found some information about this topic, but the documentation appears incomplete.

What I found:
{found_info}

What's missing:
{missing_info}

Please try:
- Being more specific about which aspect you need help with
- Using different keywords or terminology
- Breaking down your question into smaller parts"""


def format_system_prompt(retrieved_context: str, user_query: str) -> str:
    """
    Format the system prompt with retrieved context and user query.
    
    Args:
        retrieved_context: The documentation context retrieved from knowledge base
        user_query: The user's question
        
    Returns:
        Formatted system prompt string
    """
    if not retrieved_context or retrieved_context.strip() == "":
        return NO_CONTEXT_MESSAGE
    
    return SYSTEM_PROMPT_TEMPLATE.format(
        retrieved_context=retrieved_context,
        user_query=user_query
    )


def format_incomplete_context_message(found_info: str, missing_info: str) -> str:
    """
    Format a message when context is incomplete.
    
    Args:
        found_info: What information was found
        missing_info: What information is missing
        
    Returns:
        Formatted incomplete context message
    """
    return INCOMPLETE_CONTEXT_TEMPLATE.format(
        found_info=found_info,
        missing_info=missing_info
    )


# Quick reference for common Adobe Analytics terms
ADOBE_TERMINOLOGY = {
    "eVar": "Conversion variable (persists across visits)",
    "prop": "Traffic variable (page-level only)",
    "s.t()": "Page view beacon (s.track)",
    "s.tl()": "Link tracking beacon (s.trackLink)",
    "Workspace": "Modern analytics workspace (replaces Reports & Analytics)",
    "Segment": "Filtered subset of data",
    "Calculated Metric": "Custom metric created from existing metrics",
    "Virtual Report Suite": "Filtered view of a parent report suite",
    "Data View": "CJA equivalent of report suite",
    "Connection": "CJA data source connector",
    "Derived Field": "CJA field transformation at query time"
}


def get_adobe_term_definition(term: str) -> str:
    """
    Get definition for an Adobe Analytics term.
    
    Args:
        term: The term to look up
        
    Returns:
        Definition string or empty string if not found
    """
    return ADOBE_TERMINOLOGY.get(term.lower(), "")


# Validation helpers
def validate_context_quality(retrieved_context: str) -> dict:
    """
    Validate the quality of retrieved context.
    
    Args:
        retrieved_context: The retrieved documentation context
        
    Returns:
        Dictionary with validation results
    """
    if not retrieved_context:
        return {
            "valid": False,
            "reason": "Empty context",
            "suggestion": "Try different keywords or rephrase the question"
        }
    
    context_length = len(retrieved_context)
    
    if context_length < 100:
        return {
            "valid": False,
            "reason": "Context too short",
            "suggestion": "Context may be incomplete, try more specific terms"
        }
    
    return {
        "valid": True,
        "reason": "Context looks good",
        "context_length": context_length
    }


def should_use_fallback(retrieved_context: str, min_context_length: int = 100) -> bool:
    """
    Determine if fallback message should be used.
    
    Args:
        retrieved_context: The retrieved documentation context
        min_context_length: Minimum acceptable context length
        
    Returns:
        True if fallback should be used, False otherwise
    """
    if not retrieved_context:
        return True
    
    if len(retrieved_context.strip()) < min_context_length:
        return True
    
    return False

