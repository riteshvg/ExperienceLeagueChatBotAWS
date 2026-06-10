"""
Strands-based RAG pipeline.

Replaces the fixed single-pass pipeline in rag_pipeline.py with an agent
that can decide to search multiple times before answering — fixing the
shallow answer problem when the first retrieval is insufficient.

Usage (drop-in for RAGPipeline.stream):
    pipeline = StrandsPipeline(retriever, session_store)
    async for event in pipeline.stream(query, session_id):
        yield event
"""

import json
import logging
import sys
from pathlib import Path
from typing import AsyncGenerator

from strands import Agent, tool
from strands.models.bedrock import BedrockModel

_PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.core.chroma_retriever import ChromaRetriever
from backend.core.session_store import SessionStore
from config.prompts import build_conversation_history, NO_CONTEXT_MESSAGE
from config.settings import get_settings
from backend.core.query_processor import QueryProcessor

logger = logging.getLogger(__name__)

# ── Agent system prompt ───────────────────────────────────────────────────────

_AGENT_SYSTEM_PROMPT = """You are a senior Adobe Experience Cloud solutions consultant \
with deep expertise in Adobe Analytics, Customer Journey Analytics (CJA), and \
Adobe Experience Platform (AEP).

Your audience is Adobe practitioners — analysts, data engineers, and implementation \
consultants who expect precise, complete, actionable answers.

INSTRUCTIONS:
1. Always call search_documentation at least once before answering.
2. After reviewing the results, if the context is incomplete or missing key steps, \
call search_documentation again with a more specific or different query.
3. You may search up to 3 times to gather sufficient context.
4. Once you have enough context, synthesize a complete answer.
5. Never invent features, UI paths, or procedures not in the retrieved documentation.
6. For procedural questions: number every step, state prerequisites first.
7. Use **bold** for UI elements and `code` for API/function names.
8. Do not add closing filler like "I hope this helps."
9. If after 3 searches the context is still insufficient, say what was found \
and what is missing."""


# ── Tool registry (populated at pipeline init) ───────────────────────────────

_retriever_ref: ChromaRetriever | None = None
_query_processor_ref: QueryProcessor | None = None
_collected_citations: list = []


@tool
def search_documentation(query: str) -> str:
    """
    Search Adobe Experience League documentation for information relevant to the query.
    Returns the most relevant documentation chunks. Call this whenever you need
    information about Adobe Analytics, CJA, or AEP features, procedures, or concepts.

    Args:
        query: The search query — be specific, use Adobe terminology.
    """
    global _retriever_ref, _query_processor_ref, _collected_citations

    if not _retriever_ref:
        return "Search unavailable — retriever not initialised."

    # Expand Adobe abbreviations
    enhanced, _ = _query_processor_ref.preprocess_query(query)
    settings = get_settings()

    docs = _retriever_ref.retrieve(
        enhanced,
        n_results=8,
        similarity_threshold=settings.similarity_threshold,
    )

    if not docs:
        return f"No documentation found for: {query}"

    # Collect citations for later
    for doc in docs:
        meta = doc.get("metadata", {})
        url = meta.get("url", "")
        if url.startswith("https://experienceleague.adobe.com"):
            citation = {"url": url, "title": meta.get("title", ""), "product": meta.get("product", ""), "score": doc.get("score", 0.0)}
            if citation not in _collected_citations:
                _collected_citations.append(citation)

    # Return formatted context to the agent
    parts = []
    for i, doc in enumerate(docs, 1):
        title = doc.get("metadata", {}).get("title", f"Document {i}")
        parts.append(f"[{i}] {title}\n{doc['content']}")

    return "\n\n---\n\n".join(parts)


# ── Pipeline class ────────────────────────────────────────────────────────────

class StrandsPipeline:
    """Drop-in replacement for RAGPipeline using Strands agent."""

    def __init__(self, retriever: ChromaRetriever, session_store: SessionStore):
        self.retriever = retriever
        self.session_store = session_store
        self.query_processor = QueryProcessor()

        settings = get_settings()
        self.model = BedrockModel(
            model_id=settings.bedrock_model_id,
            region_name=settings.bedrock_region,
        )

    async def stream(
        self,
        query: str,
        session_id: str,
        haiku_only: bool = False,
    ) -> AsyncGenerator[dict, None]:
        """
        Yields SSE-style dicts identical to RAGPipeline.stream:
          {"type": "token",     "content": str}
          {"type": "citations", "citations": list}
          {"type": "done",      "model": str, "session_id": str}
          {"type": "error",     "message": str}
        """
        global _retriever_ref, _query_processor_ref, _collected_citations

        # Wire tools to this request's retriever
        _retriever_ref = self.retriever
        _query_processor_ref = self.query_processor
        _collected_citations = []

        try:
            # Build conversation context
            history = self.session_store.get_history(session_id)
            conversation_history = build_conversation_history(history)
            full_query = query
            if conversation_history:
                full_query = f"Prior conversation:\n{conversation_history}\n\nCurrent question: {query}"

            # Pick model
            settings = get_settings()
            model_id = settings.bedrock_model_id
            if haiku_only:
                model_id = "anthropic.claude-3-haiku-20240307-v1:0"

            model_label = "haiku" if "haiku" in model_id else "sonnet" if "sonnet" in model_id else "opus"

            bedrock_model = BedrockModel(
                model_id=model_id,
                region_name=settings.bedrock_region,
            )

            agent = Agent(
                model=bedrock_model,
                tools=[search_documentation],
                system_prompt=_AGENT_SYSTEM_PROMPT,
            )

            # Collect full response (Strands doesn't natively support async SSE streaming)
            full_response = ""
            response = agent(full_query)
            full_response = str(response)

            # Stream the response token by token (word-level)
            words = full_response.split(" ")
            for i, word in enumerate(words):
                chunk = word + (" " if i < len(words) - 1 else "")
                yield {"type": "token", "content": chunk}

            # Persist turn
            self.session_store.append_turn(session_id, "user", query)
            self.session_store.append_turn(session_id, "assistant", full_response)

            yield {"type": "citations", "citations": _collected_citations[:5]}
            yield {"type": "done", "model": model_label, "session_id": session_id}

        except Exception as exc:
            logger.exception("Strands pipeline error")
            yield {"type": "error", "message": str(exc)}
