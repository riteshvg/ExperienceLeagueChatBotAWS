"""
RAG pipeline — LangChain LCEL edition.

Architecture:
  QueryProcessor → ChromaRetriever → LangChain chain (prompt | ChatAnthropic | StrOutputParser)

LangChain components used:
  - ChatAnthropic       : streaming LLM
  - ChatPromptTemplate  : structured prompt with context + history placeholders
  - MessagesPlaceholder : injects conversation history as typed messages
  - StrOutputParser     : extracts text from AIMessage chunks
  - LCEL (|)            : composes the chain declaratively
"""

import logging
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

# ── LangChain prompt template ────────────────────────────────────────────────
_SYSTEM_TEMPLATE = """You are an Adobe Experience League documentation assistant. \
Answer questions accurately using only the retrieved documentation context below. \
If the context does not contain enough information to answer, say so clearly — do not hallucinate.

Retrieved context:
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

            # 1. Expand Adobe abbreviations
            enhanced_query, _ = self.query_processor.preprocess_query(query)

            # 2. Vector retrieval via existing ChromaRetriever (Titan embeddings)
            raw_docs = self.retriever.retrieve(
                enhanced_query,
                n_results=settings.max_retrieval_results,
                similarity_threshold=settings.similarity_threshold,
            )

            if not raw_docs:
                yield {"type": "token", "content": NO_CONTEXT_MESSAGE}
                yield {"type": "done", "model": "none", "session_id": session_id}
                return

            # 3. Build context + extract citations from retrieved doc metadata
            context = "\n\n---\n\n".join(doc["content"] for doc in raw_docs)
            citations = [
                c for doc in raw_docs
                if (c := format_citation(doc, doc_title=doc.get("metadata", {}).get("title"))).get("url", "").startswith("https://experienceleague.adobe.com")
            ]

            # 4. Convert session history to LangChain messages
            lc_history = _to_lc_history(self.session_store.get_history(session_id))

            # 5. Pick model + build LCEL chain
            model_id = _HAIKU_MODEL if haiku_only else _SONNET_MODEL
            model_label = "haiku" if "haiku" in model_id else "sonnet" if "sonnet" in model_id else "opus"
            chain = _build_chain(model_id, settings.anthropic_api_key)

            # 6. Stream via LangChain LCEL .astream()
            full_response = ""
            async for chunk in chain.astream({
                "context": context,
                "history": lc_history,
                "query": query,
            }):
                full_response += chunk
                yield {"type": "token", "content": chunk}

            # 7. Persist turn to session store
            self.session_store.append_turn(session_id, "user", query)
            self.session_store.append_turn(session_id, "assistant", full_response)

            # 8. Emit citations + done
            yield {"type": "citations", "citations": citations}
            yield {"type": "done", "model": model_label, "session_id": session_id}

        except Exception as exc:
            logger.exception("RAG pipeline error")
            yield {"type": "error", "message": str(exc)}
