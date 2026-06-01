"""
RAG pipeline: composes existing src/ utilities with ChromaDB retrieval.

This replaces the monolithic query handler in app.py, delegating to the
same modules (query_processor, citation_mapper, prompts, streaming_bedrock_client)
so no business logic needs to be re-implemented.
"""

import logging
import sys
from pathlib import Path
from typing import AsyncGenerator, Optional

# ── project root on sys.path so relative imports work ──────────────────────
_PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.core.chroma_retriever import ChromaRetriever
from backend.core.session_store import SessionStore
from config.prompts import build_conversation_history, format_system_prompt, NO_CONTEXT_MESSAGE
from config.settings import get_settings
from src.utils.citation_mapper import format_citation
from src.utils.query_processor import QueryProcessor
from src.utils.streaming_bedrock_client import StreamingBedrockClient
from src.utils.url_validator import filter_valid_citations

logger = logging.getLogger(__name__)

_settings = get_settings()

# Model IDs
_HAIKU_MODEL = "anthropic.claude-3-haiku-20240307-v1:0"
_SONNET_MODEL = _settings.bedrock_model_id  # 3.7 Sonnet by default


class RAGPipeline:
    """Orchestrates retrieval → prompt assembly → streaming generation."""

    def __init__(self, retriever: ChromaRetriever, session_store: SessionStore):
        self.retriever = retriever
        self.session_store = session_store
        self.query_processor = QueryProcessor()

    # ── Public streaming interface ──────────────────────────────────────────

    async def stream(
        self,
        query: str,
        session_id: str,
        haiku_only: bool = False,
    ) -> AsyncGenerator[dict, None]:
        """
        Async generator yielding SSE-style dicts:
          {"type": "token", "content": str}
          {"type": "citations", "citations": list[dict]}
          {"type": "done", "model": str, "session_id": str}
          {"type": "error", "message": str}
        """
        try:
            # 1. Expand Adobe abbreviations
            enhanced_query, _ = self.query_processor.preprocess_query(query)
            logger.debug(f"Enhanced query: {enhanced_query!r}")

            # 2. Vector retrieval — re-read settings each call so .env changes take effect
            live_settings = get_settings()
            raw_docs = self.retriever.retrieve(
                enhanced_query,
                n_results=live_settings.max_retrieval_results,
                similarity_threshold=live_settings.similarity_threshold,
            )

            if not raw_docs:
                yield {"type": "token", "content": NO_CONTEXT_MESSAGE}
                yield {"type": "done", "model": "none", "session_id": session_id}
                return

            # 3. Build context string + citations
            context_parts: list[str] = []
            citations: list[dict] = []
            for doc in raw_docs:
                context_parts.append(doc["content"])
                citation = format_citation(doc, doc_title=doc.get("metadata", {}).get("title"))
                if citation.get("url"):
                    citations.append(citation)

            retrieved_context = "\n\n---\n\n".join(context_parts)

            # 4. Build conversation history
            history = self.session_store.get_history(session_id)
            conversation_history = build_conversation_history(history)

            # 5. Assemble prompt
            prompt = format_system_prompt(
                retrieved_context=retrieved_context,
                user_query=query,
                conversation_history=conversation_history,
            )

            # 6. Pick model
            model_id = _HAIKU_MODEL if haiku_only else _SONNET_MODEL
            # Derive label from actual model ID
            if "haiku" in model_id:
                model_label = "haiku"
            elif "sonnet" in model_id:
                model_label = "sonnet"
            elif "opus" in model_id:
                model_label = "opus"
            else:
                model_label = model_id.split(".")[-1]

            # 7. Stream generation
            client = StreamingBedrockClient(
                model_id=model_id,
                region=_settings.bedrock_region,
            )
            full_response = ""
            for chunk in client.generate_streaming_text(prompt, max_tokens=4000):
                full_response += chunk
                yield {"type": "token", "content": chunk}

            # 8. Persist turn
            self.session_store.append_turn(session_id, "user", query)
            self.session_store.append_turn(session_id, "assistant", full_response)

            # 9. Emit citations — only include ones with a non-empty URL
            citations = [c for c in citations if c.get("url", "").startswith("https://experienceleague.adobe.com")]
            yield {"type": "citations", "citations": citations}
            yield {"type": "done", "model": model_label, "session_id": session_id}

        except Exception as exc:
            logger.exception("RAG pipeline error")
            yield {"type": "error", "message": str(exc)}
