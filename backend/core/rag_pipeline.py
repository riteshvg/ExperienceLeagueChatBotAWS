"""
RAG pipeline — LangChain LCEL + LangGraph Strands-style agent.

Routing:
  Haiku queries → single-pass LCEL chain  (fast, cheap, definitions/lookups)
  Sonnet queries → LangGraph ReAct agent  (multi-pass retrieval, complex tasks)

The agent calls search_documentation() up to 3 times before answering,
fixing shallow responses when the first retrieval misses key steps.
"""

import json as _json
import logging
import re
import sys
from pathlib import Path
from typing import AsyncGenerator

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

_PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.core.chroma_retriever import ChromaRetriever
from backend.core.session_store import SessionStore
from backend.core.smart_router import classify_query, detect_product_intent
from config.prompts import NO_CONTEXT_MESSAGE
from config.settings import get_settings
from backend.core.query_processor import QueryProcessor
from src.utils.exl_url_mapper import is_specific_url

logger = logging.getLogger(__name__)

_HAIKU_MODEL  = "claude-haiku-4-5-20251001"
_SONNET_MODEL = "claude-sonnet-4-6"

# Returned directly (no LLM) when the query is clearly off-topic
_OUT_OF_SCOPE_RESPONSE = (
    "I can only answer questions about Adobe Analytics, CJA, AEP, Adobe Target, "
    "Adobe Journey Optimizer, and Adobe Data Collection.\n\n"
    "That topic is outside my area of expertise. I specialise exclusively in:\n\n"
    "- **Adobe Analytics** – reporting, data collection, implementation\n"
    "- **Customer Journey Analytics (CJA)** – cross-channel analysis, connections, data views\n"
    "- **Adobe Experience Platform (AEP)** – schemas, datasets, segments, destinations, RTCDP\n"
    "- **Adobe Target** – A/B testing, personalisation, recommendations\n"
    "- **Adobe Journey Optimizer (AJO)** – journeys, campaigns, decision management\n"
    "- **Adobe Data Collection** – Tags/Launch, Web SDK, Mobile SDK, Datastreams, Edge Network\n\n"
    "Please ask me anything related to these products and I'll be happy to help! 😊"
)

_FOLLOWUP_PATTERNS = re.compile(
    r'\b(it|this|that|one|them|they|those|these|the same|the above|do so|how do i|can i|steps|process)\b',
    re.IGNORECASE,
)

# ── Shared system prompts ─────────────────────────────────────────────────────

_HAIKU_SYSTEM = """You are an Adobe Experience League documentation assistant. \
You ONLY answer questions about Adobe products: Adobe Analytics, Customer Journey Analytics (CJA), \
Adobe Experience Platform (AEP), Adobe Target, Adobe Journey Optimizer (AJO), and Adobe Data Collection \
(Tags/Launch, Web SDK, Datastreams, Edge Network).

If the question is not about these Adobe products, respond with:
"I can only answer questions about Adobe Analytics, CJA, AEP, Adobe Target, Adobe Journey Optimizer, \
and Adobe Data Collection. Please ask about these products."

Guidelines for Adobe questions:
- Answer as completely as possible using the retrieved context.
- Use headers, bullet points, and numbered steps where helpful.
- Do NOT redirect users to "check the documentation" — synthesize the information.
- Only say you don't know if the topic is completely absent from the context.

Media embedding rules:
- Embed images inline using: ![description](url)
- Embed videos inline using: [▶ Watch: Brief Title](video_url)
- Place media naturally after the relevant paragraph.

Retrieved documentation context:
{context}"""

_AGENT_SYSTEM = """You are a senior Adobe Experience Cloud solutions consultant with deep \
expertise in Adobe Analytics, Customer Journey Analytics (CJA), Adobe Experience Platform (AEP), \
Adobe Target, Adobe Journey Optimizer (AJO), and Adobe Data Collection (Tags/Launch, Web SDK, \
Datastreams, Edge Network).

You ONLY answer questions about these Adobe products. If asked about anything unrelated \
(food, general knowledge, other software, etc.), respond:
"I can only answer questions about Adobe Analytics, CJA, AEP, Adobe Target, Adobe Journey Optimizer, \
and Adobe Data Collection."

INSTRUCTIONS for Adobe questions:
1. Always call search_documentation at least once before answering.
2. After reviewing the results, if the context is incomplete or missing key steps, \
call search_documentation again with a more specific or different query.
3. You may search up to 3 times to gather sufficient context.
4. Once you have enough context, synthesize a complete, step-by-step answer.
5. Never invent features, UI paths, or procedures not in the retrieved documentation.
6. For procedural questions: number every step, state prerequisites first.
7. Use **bold** for UI elements and `code` for API/function names.
8. Embed images inline using: ![description](url)
9. Embed videos inline using: [▶ Watch: Brief Title](video_url)
10. Place media naturally after the relevant paragraph — not all grouped at the end."""

_HAIKU_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _HAIKU_SYSTEM),
    MessagesPlaceholder("history"),
    ("human", "{query}"),
])


# ── LCEL chain (Haiku) ────────────────────────────────────────────────────────

def _build_haiku_chain(api_key: str):
    llm = ChatAnthropic(model=_HAIKU_MODEL, api_key=api_key, max_tokens=2000, streaming=True)
    return _HAIKU_PROMPT | llm | StrOutputParser()


# ── LangGraph agent (Sonnet) ─────────────────────────────────────────────────

def _make_search_tool(retriever: ChromaRetriever, query_processor: QueryProcessor,
                      settings, citations_out: list,
                      where_filter: dict | None = None):
    """Create a search_documentation tool scoped to this request's retriever."""

    @tool
    def search_documentation(query: str) -> str:
        """
        Search Adobe Experience League documentation for the given query.
        Call this whenever you need information about Adobe Analytics, CJA, AEP, AJO, or Target.
        Use specific Adobe terminology. Call multiple times with refined queries if needed.

        Args:
            query: The search query — be specific.
        """
        enhanced, _ = query_processor.preprocess_query(query)
        docs = retriever.retrieve(
            enhanced,
            n_results=settings.max_retrieval_results,
            similarity_threshold=settings.similarity_threshold,
            where=where_filter,
        )
        if not docs:
            return f"No documentation found for: {query}"

        # Snapshot offset so numbering is globally consistent across multiple tool calls
        offset = len(citations_out)

        parts = []
        for i, doc in enumerate(docs, 1):
            meta = doc.get("metadata", {})
            title = meta.get("title", f"Document {i}")

            # Collect citations — deduplicated by URL, only specific pages
            url = meta.get("url", "")
            citation_num: int | None = None
            if is_specific_url(url):
                existing_idx = next(
                    (j for j, x in enumerate(citations_out) if x.get("url") == url), None
                )
                if existing_idx is not None:
                    citation_num = existing_idx + 1
                else:
                    c: dict = {
                        "url": url,
                        "title": title,
                        "product": meta.get("product", ""),
                        "score": doc.get("score", 0.0),
                    }
                    if meta.get("video_url"):
                        c["video_url"] = meta["video_url"]
                    if meta.get("thumbnail_url"):
                        c["thumbnail_url"] = meta["thumbnail_url"]
                    if meta.get("image_urls"):
                        try:
                            c["image_urls"] = _json.loads(meta["image_urls"])
                        except Exception:
                            pass
                    citations_out.append(c)
                    citation_num = len(citations_out)

            # Use citation_num for perfect alignment; fall back to offset+i for filtered docs
            doc_num = citation_num if citation_num is not None else offset + i

            # Build text block with media hints for inline embedding
            block = f"[{doc_num}] {title}\n{doc['content']}"
            media_hints = []
            if meta.get("image_urls"):
                try:
                    for url in _json.loads(meta["image_urls"])[:2]:
                        media_hints.append(f"Image: {url}")
                except Exception:
                    pass
            if meta.get("video_url"):
                media_hints.append(f"Video: {meta['video_url']} (Title: {title})")
            if media_hints:
                block += "\n\nAVAILABLE MEDIA (embed inline where relevant):\n" + "\n".join(media_hints)
            parts.append(block)

        return "\n\n---\n\n".join(parts)

    return search_documentation


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
    images, videos = [], []
    seen_imgs, seen_vids = set(), set()
    for doc in docs:
        meta = doc.get("metadata", {})
        raw = meta.get("image_urls", "")
        if raw:
            try:
                for url in _json.loads(raw):
                    if url not in seen_imgs and len(images) < 4:
                        images.append(url); seen_imgs.add(url)
            except Exception:
                pass
        v = meta.get("video_url", "")
        if v and v not in seen_vids and len(videos) < 2:
            videos.append({"url": v, "title": meta.get("title", "Video")}); seen_vids.add(v)
    if not images and not videos:
        return ""
    lines = ["\n---\nAvailable media — embed inline where relevant:"]
    if images:
        lines.append("Images (use ![alt](url) markdown):")
        for url in images:
            lines.append(f"  - {url}")
    if videos:
        lines.append("Videos (embed as [▶ Watch: Short Title](url)):")
        for v in videos:
            lines.append(f"  - {v['title']} → {v['url']}")
    return "\n".join(lines)


# ── Pipeline ──────────────────────────────────────────────────────────────────

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

            # Route: haiku_only flag overrides auto-routing
            routed = "haiku" if haiku_only else classify_query(query)
            logger.info(f"SmartRouter: '{query[:60]}' → {routed}")

            if routed == "sonnet":
                async for event in self._stream_agent(query, session_id, history, settings):
                    yield event
            else:
                async for event in self._stream_chain(query, session_id, history, settings):
                    yield event

        except Exception as exc:
            logger.exception("RAG pipeline error")
            yield {"type": "error", "message": str(exc)}

    # ── Haiku: single-pass LCEL chain ─────────────────────────────────────────

    async def _stream_chain(self, query, session_id, history, settings):
        enhanced, _ = self.query_processor.preprocess_query(query)
        search_query = _contextualize_query(enhanced, history)

        product_intent = detect_product_intent(query)
        where_filter = {"product": {"$eq": product_intent}} if product_intent else None

        raw_docs = self.retriever.retrieve(
            search_query,
            n_results=settings.max_retrieval_results,
            similarity_threshold=settings.similarity_threshold,
            where=where_filter,
        )
        if not raw_docs:
            yield {"type": "token", "content": NO_CONTEXT_MESSAGE}
            yield {"type": "done", "model": "none", "session_id": session_id}
            return

        # Off-topic detection: if best match score < 0.25, skip LLM entirely
        off_topic = self._is_off_topic(raw_docs)
        if off_topic:
            yield {"type": "token", "content": _OUT_OF_SCOPE_RESPONSE}
            self.session_store.append_turn(session_id, "user", query)
            self.session_store.append_turn(session_id, "assistant", _OUT_OF_SCOPE_RESPONSE)
            yield {"type": "citations", "citations": []}
            yield {"type": "done", "model": "none", "session_id": session_id,
                   "input_tokens": 0, "output_tokens": 0}
            return

        # Number docs so the LLM can cite [1], [2], etc. inline
        context = "\n\n---\n\n".join(
            f"[{i+1}] {doc['content']}" for i, doc in enumerate(raw_docs)
        )
        context += _build_media_context(raw_docs)

        citations = [] if off_topic else self._extract_citations(raw_docs)
        lc_history = _to_lc_history(history)
        chain = _build_haiku_chain(settings.anthropic_api_key)

        full_response = ""
        async for chunk in chain.astream({"context": context, "history": lc_history, "query": query}):
            full_response += chunk
            yield {"type": "token", "content": chunk}

        self.session_store.append_turn(session_id, "user", query)
        self.session_store.append_turn(session_id, "assistant", full_response)
        yield {"type": "citations", "citations": citations}
        # Estimate token counts from text lengths (÷4 chars per token)
        input_tokens = (len(_HAIKU_SYSTEM) + len(context) + len(query)
                        + sum(len(getattr(m, "content", "")) for m in lc_history)) // 4
        output_tokens = len(full_response) // 4
        yield {"type": "done", "model": "haiku", "session_id": session_id,
               "input_tokens": input_tokens, "output_tokens": output_tokens}

    # ── Sonnet: LangGraph multi-pass agent ────────────────────────────────────

    async def _stream_agent(self, query, session_id, history, settings):
        # Pre-check: skip expensive Sonnet agent for clearly off-topic queries
        product_intent = detect_product_intent(query)
        where_filter = {"product": {"$eq": product_intent}} if product_intent else None

        probe_docs = self.retriever.retrieve(
            query,
            n_results=settings.max_retrieval_results,
            similarity_threshold=settings.similarity_threshold,
            where=where_filter,
        )
        if self._is_off_topic(probe_docs):
            yield {"type": "token", "content": _OUT_OF_SCOPE_RESPONSE}
            self.session_store.append_turn(session_id, "user", query)
            self.session_store.append_turn(session_id, "assistant", _OUT_OF_SCOPE_RESPONSE)
            yield {"type": "citations", "citations": []}
            yield {"type": "done", "model": "none", "session_id": session_id,
                   "input_tokens": 0, "output_tokens": 0}
            return

        citations_out: list = []
        search_tool = _make_search_tool(
            self.retriever, self.query_processor, settings, citations_out,
            where_filter=where_filter,
        )

        llm = ChatAnthropic(
            model=_SONNET_MODEL,
            api_key=settings.anthropic_api_key,
            max_tokens=4000,
            streaming=True,
        )

        agent = create_react_agent(
            llm,
            tools=[search_tool],
            prompt=SystemMessage(content=_AGENT_SYSTEM),
        )

        # Build message history
        messages = _to_lc_history(history) + [HumanMessage(content=query)]

        full_response = ""
        try:
            async for event in agent.astream_events(
                {"messages": messages},
                version="v2",
            ):
                if event["event"] == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    content = chunk.content
                    # Claude with tool use returns content as a list of blocks
                    # e.g. [{"type": "text", "text": "..."}] or [] for tool calls
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "text":
                                text = block.get("text", "")
                                if text:
                                    full_response += text
                                    yield {"type": "token", "content": text}
                    elif isinstance(content, str) and content:
                        full_response += content
                        yield {"type": "token", "content": content}

        except Exception as exc:
            logger.exception("Agent stream error")
            yield {"type": "error", "message": str(exc)}
            return

        self.session_store.append_turn(session_id, "user", query)
        self.session_store.append_turn(session_id, "assistant", full_response)
        yield {"type": "citations", "citations": citations_out[:8]}
        input_tokens = (len(_AGENT_SYSTEM)
                        + sum(len(getattr(m, "content", "")) for m in messages)) // 4
        output_tokens = len(full_response) // 4
        yield {"type": "done", "model": "sonnet", "session_id": session_id,
               "input_tokens": input_tokens, "output_tokens": output_tokens}

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _extract_citations(self, raw_docs: list) -> list:
        """Extract citations from ChromaDB metadata, deduplicated by URL."""
        seen_urls: set = set()
        citations = []
        for doc in raw_docs:
            meta = doc.get("metadata", {})
            url = meta.get("url", "")
            if not is_specific_url(url):
                continue
            if url in seen_urls:
                continue
            seen_urls.add(url)
            c: dict = {
                "url": url,
                "title": meta.get("title", ""),
                "product": meta.get("product", ""),
                "score": doc.get("score", 0.0),
            }
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
        return citations

    @staticmethod
    def _is_off_topic(raw_docs: list, threshold: float = 0.25) -> bool:
        """Return True if the retrieved docs are too dissimilar — off-topic query."""
        if not raw_docs:
            return True
        return max(d.get("score", 0) for d in raw_docs) < threshold
