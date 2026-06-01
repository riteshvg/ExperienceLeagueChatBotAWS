"""
RAG pipeline — LangChain LCEL edition.

Architecture:
  QueryProcessor → query contextualization → ChromaRetriever → LangChain chain

Media handling:
  Images and video URLs are extracted from ChromaDB metadata and injected into
  the prompt context so Claude can embed them inline in the answer naturally,
  rather than appending them as a separate section.
"""

import json as _json
import logging
import re
import sys
from pathlib import Path
from typing import AsyncGenerator

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

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

_FOLLOWUP_PATTERNS = re.compile(
    r'\b(it|this|that|one|them|they|those|these|the same|the above|do so|how do i|can i|steps|process)\b',
    re.IGNORECASE
)

_SYSTEM_TEMPLATE = """You are an expert Adobe Experience League documentation assistant. \
Give thorough, step-by-step answers grounded in the retrieved documentation below.

Guidelines:
- Answer as completely as possible using the retrieved context.
- Use headers, bullet points, and numbered steps to make answers easy to follow.
- Do NOT redirect users to "check the documentation" — synthesize the information.
- Only say you don't know if the topic is completely absent from the context.

Media embedding rules (IMPORTANT):
- If images are provided in the context, embed them inline using standard markdown: ![description](url)
- Place each image immediately after the paragraph or step it illustrates.
- If a video is provided, embed it as a link inline: [▶ Watch: Brief Title](video_url)
- Place media naturally where it helps comprehension — NOT all grouped at the end.
- Only include media that directly illustrates the point being made.

Retrieved documentation context:
{context}"""

_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM_TEMPLATE),
    MessagesPlaceholder("history"),
    ("human", "{query}"),
])


def _build_chain(model_id: str, api_key: str):
    llm = ChatAnthropic(model=model_id, api_key=api_key, max_tokens=4000, streaming=True)
    return _PROMPT | llm | StrOutputParser()


def _to_lc_history(history: list[dict]) -> list:
    messages = []
    for turn in history:
        if turn["role"] == "user":
            messages.append(HumanMessage(content=turn["content"]))
        else:
            messages.append(AIMessage(content=turn["content"]))
    return messages


def _contextualize_query(query: str, history: list[dict]) -> str:
    if not history or not _FOLLOWUP_PATTERNS.search(query):
        return query
    last_user = next((t["content"] for t in reversed(history) if t["role"] == "user"), None)
    if last_user and len(query.split()) <= 12:
        return f"{last_user} — {query}"
    return query


def _build_media_context(docs: list[dict]) -> str:
    """
    Collect unique images and videos from retrieved docs and format them
    as a prompt section so Claude can embed them inline.
    """
    images: list[str] = []
    videos: list[dict] = []
    seen_images: set[str] = set()
    seen_videos: set[str] = set()

    for doc in docs:
        meta = doc.get("metadata", {})

        # Images
        raw_imgs = meta.get("image_urls", "")
        if raw_imgs:
            try:
                for url in _json.loads(raw_imgs):
                    if url not in seen_images and len(images) < 4:
                        images.append(url)
                        seen_images.add(url)
            except Exception:
                pass

        # Videos
        video_url = meta.get("video_url", "")
        title = meta.get("title", "Related video")
        if video_url and video_url not in seen_videos and len(videos) < 2:
            videos.append({"url": video_url, "title": title})
            seen_videos.add(video_url)

    if not images and not videos:
        return ""

    lines = ["\n---\nAvailable media — embed inline where relevant:"]
    if images:
        lines.append("Images (use ![alt text](url) markdown inline):")
        for url in images:
            lines.append(f"  - {url}")
    if videos:
        lines.append("Videos (embed as [▶ Watch: Short Title](url) inline):")
        for v in videos:
            lines.append(f"  - {v['title']} → {v['url']}")

    return "\n".join(lines)


class RAGPipeline:
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
        try:
            settings = get_settings()
            history = self.session_store.get_history(session_id)

            enhanced_query, _ = self.query_processor.preprocess_query(query)
            search_query = _contextualize_query(enhanced_query, history)

            raw_docs = self.retriever.retrieve(
                search_query,
                n_results=settings.max_retrieval_results,
                similarity_threshold=settings.similarity_threshold,
            )

            if not raw_docs:
                yield {"type": "token", "content": NO_CONTEXT_MESSAGE}
                yield {"type": "done", "model": "none", "session_id": session_id}
                return

            # Build text context + append media section for Claude to embed inline
            text_context = "\n\n---\n\n".join(doc["content"] for doc in raw_docs)
            media_context = _build_media_context(raw_docs)
            context = text_context + media_context

            # Build citations for source pills
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
                        c["image_urls"] = _json.loads(meta["image_urls"])
                    except Exception:
                        pass
                citations.append(c)

            lc_history = _to_lc_history(history)
            model_id = _HAIKU_MODEL if haiku_only else _SONNET_MODEL
            model_label = "haiku" if "haiku" in model_id else "sonnet" if "sonnet" in model_id else "opus"
            chain = _build_chain(model_id, settings.anthropic_api_key)

            full_response = ""
            async for chunk in chain.astream({
                "context": context,
                "history": lc_history,
                "query": query,
            }):
                full_response += chunk
                yield {"type": "token", "content": chunk}

            self.session_store.append_turn(session_id, "user", query)
            self.session_store.append_turn(session_id, "assistant", full_response)

            yield {"type": "citations", "citations": citations}
            yield {"type": "done", "model": model_label, "session_id": session_id}

        except Exception as exc:
            logger.exception("RAG pipeline error")
            yield {"type": "error", "message": str(exc)}
