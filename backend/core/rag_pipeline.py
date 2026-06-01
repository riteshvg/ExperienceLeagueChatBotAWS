"""
RAG pipeline — LangChain LCEL edition.

Architecture:
  QueryProcessor → query contextualization → ChromaRetriever → LangChain chain

LangChain components:
  - ChatAnthropic       : streaming LLM
  - ChatPromptTemplate  : structured prompt with context + history placeholders
  - MessagesPlaceholder : injects conversation history as typed messages
  - StrOutputParser     : extracts text from AIMessage chunks
  - LCEL (|)            : composes the chain declaratively
"""

import logging
import re
import sys
from pathlib import Path
from typing import AsyncGenerator

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# ── project root on sys.path ────────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.core.chroma_retriever import ChromaRetriever
from backend.core.session_store import SessionStore
from config.prompts import NO_CONTEXT_MESSAGE
from config.settings import get_settings
from src.utils.citation_mapper import format_citation
from src.utils.query_processor import QueryProcessor

logger = logging.getLogger(__name__)

_HAIKU_MODEL = "claude-haiku-4-5-20251001"
_SONNET_MODEL = "claude-sonnet-4-6"

# Pronouns and vague references that signal a follow-up query needing context
_FOLLOWUP_PATTERNS = re.compile(
    r'\b(it|this|that|one|them|they|those|these|the same|the above|do so|how do i|can i|steps|process)\b',
    re.IGNORECASE
)

# ── LangChain prompt template ────────────────────────────────────────────────
_SYSTEM_TEMPLATE = """You are an expert Adobe Experience League documentation assistant. \
Your job is to give thorough, detailed, step-by-step answers grounded in the retrieved documentation below.

Guidelines:
- Always answer as completely as possible using the retrieved context.
- If the context covers the topic partially, provide what you know and clearly note any gaps.
- Use headers, bullet points, and numbered steps to make answers easy to follow.
- Do NOT just redirect users to "check the documentation" — synthesize the information for them.
- Only say you don't know if the topic is completely absent from the context.
- When steps or procedures are available in the context, list them explicitly.

Retrieved documentation context:
{context}"""

_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM_TEMPLATE),
    MessagesPlaceholder("history"),
    ("human", "{query}"),
])


def _build_chain(model_id: str, api_key: str):
    """Return a streaming LCEL chain: prompt | llm | parser."""
    llm = ChatAnthropic(
        model=model_id,
        api_key=api_key,
        max_tokens=4000,
        streaming=True,
    )
    return _PROMPT | llm | StrOutputParser()


def _to_lc_history(history: list[dict]) -> list:
    """Convert SessionStore turns to LangChain HumanMessage / AIMessage objects."""
    messages = []
    for turn in history:
        if turn["role"] == "user":
            messages.append(HumanMessage(content=turn["content"]))
        else:
            messages.append(AIMessage(content=turn["content"]))
    return messages


def _contextualize_query(query: str, history: list[dict]) -> str:
    """
    For short follow-up queries containing vague references (it, one, this, etc.),
    prepend the last user turn so the vector search has enough context to find
    the right documents. E.g. "How do I create one?" + prior "What is a Connection
    in CJA?" → "CJA Connection: How do I create one?"
    """
    if not history or not _FOLLOWUP_PATTERNS.search(query):
        return query

    # Find the last user message
    last_user = next(
        (t["content"] for t in reversed(history) if t["role"] == "user"),
        None,
    )
    if not last_user:
        return query

    # Only inject context when the query is short (likely a follow-up)
    if len(query.split()) <= 12:
        contextualized = f"{last_user} — {query}"
        logger.debug(f"Contextualized query: {contextualized!r}")
        return contextualized

    return query


class RAGPipeline:
    """Orchestrates retrieval → LangChain chain → SSE streaming."""

    def __init__(self, retriever: ChromaRetriever, session_store: SessionStore):
        self.retriever = retriever
        self.session_store = session_store
        self.query_processor = QueryProcessor()

    async def stream(
        self,
        query: str,
        session_id: str,
        haiku_only: bool = False,
    ) -> AsyncGenerator[dict, None]:
        """
        Async generator yielding SSE-style dicts:
          {"type": "token",     "content": str}
          {"type": "citations", "citations": list[dict]}
          {"type": "done",      "model": str, "session_id": str}
          {"type": "error",     "message": str}
        """
        try:
            settings = get_settings()
            history = self.session_store.get_history(session_id)

            # 1. Expand Adobe abbreviations
            enhanced_query, _ = self.query_processor.preprocess_query(query)

            # 2. Contextualize follow-up queries before embedding
            search_query = _contextualize_query(enhanced_query, history)

            # 3. Vector retrieval
            raw_docs = self.retriever.retrieve(
                search_query,
                n_results=settings.max_retrieval_results,
                similarity_threshold=settings.similarity_threshold,
            )

            if not raw_docs:
                yield {"type": "token", "content": NO_CONTEXT_MESSAGE}
                yield {"type": "done", "model": "none", "session_id": session_id}
                return

            # 4. Build context + extract citations (with media fields from ChromaDB metadata)
            context = "\n\n---\n\n".join(doc["content"] for doc in raw_docs)
            citations = []
            for doc in raw_docs:
                meta = doc.get("metadata", {})
                c = format_citation(doc, doc_title=meta.get("title"))
                if not c.get("url", "").startswith("https://experienceleague.adobe.com"):
                    continue
                if meta.get("video_url"):
                    c["video_url"] = meta["video_url"]
                if meta.get("thumbnail_url"):
                    c["thumbnail_url"] = meta["thumbnail_url"]
                if meta.get("image_urls"):
                    try:
                        import json as _json
                        c["image_urls"] = _json.loads(meta["image_urls"])
                    except Exception:
                        pass
                citations.append(c)

            # 5. Convert session history to LangChain messages
            lc_history = _to_lc_history(history)

            # 6. Pick model + build LCEL chain
            model_id = _HAIKU_MODEL if haiku_only else _SONNET_MODEL
            model_label = "haiku" if "haiku" in model_id else "sonnet" if "sonnet" in model_id else "opus"
            chain = _build_chain(model_id, settings.anthropic_api_key)

            # 7. Stream via LangChain LCEL .astream()
            full_response = ""
            async for chunk in chain.astream({
                "context": context,
                "history": lc_history,
                "query": query,
            }):
                full_response += chunk
                yield {"type": "token", "content": chunk}

            # 8. Persist turn
            self.session_store.append_turn(session_id, "user", query)
            self.session_store.append_turn(session_id, "assistant", full_response)

            # 9. Emit citations + done
            yield {"type": "citations", "citations": citations}
            yield {"type": "done", "model": model_label, "session_id": session_id}

        except Exception as exc:
            logger.exception("RAG pipeline error")
            yield {"type": "error", "message": str(exc)}
