"""
RAG pipeline — LangChain LCEL dual-model routing.

Routing:
  Haiku  → single-pass LCEL chain  (fast, cheap, definitions/lookups)
  Sonnet → single-pass LCEL chain  (higher quality, complex/procedural queries)

Both paths: retrieve once → build context → stream answer.
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
from backend.core.evidence import build_evidence
from backend.core.retrieval_refiner import (
    RefinementResult,
    refinement_to_evidence_fields,
    retrieve_with_refinement,
)
from backend.core.session_store import SessionStore
from backend.core.smart_router import classify_query, detect_product_intent
from backend.core.url_validator import filter_valid_citations
from config.prompts import NO_CONTEXT_MESSAGE
from config.settings import get_settings
from backend.core.query_processor import QueryProcessor
from src.utils.exl_url_mapper import is_specific_url, resolve_doc_url

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
- Never include links ending in .md — only use full https:// URLs.
- Do not include inline hyperlinks to Adobe documentation pages in your answer. Describe topics and guide titles by name only — source links are shown automatically in the citations panel.

Retrieved documentation context:
{context}"""

_SONNET_SYSTEM = """You are a senior Adobe Experience Cloud solutions consultant with deep \
expertise in Adobe Analytics, Customer Journey Analytics (CJA), Adobe Experience Platform (AEP), \
Adobe Target, Adobe Journey Optimizer (AJO), and Adobe Data Collection (Tags/Launch, Web SDK, \
Datastreams, Edge Network).

You ONLY answer questions about these Adobe products. If asked about anything unrelated, respond:
"I can only answer questions about Adobe Analytics, CJA, AEP, Adobe Target, Adobe Journey Optimizer, \
and Adobe Data Collection."

Guidelines for Adobe questions:
- Synthesize a complete, accurate answer using the retrieved context below.
- Never invent features, UI paths, or procedures not in the retrieved documentation.
- For procedural questions: number every step and state prerequisites first.
- Use **bold** for UI elements and `code` for API/function names.
- Use headers, bullet points, and numbered steps to structure longer answers.
- Do NOT redirect users to "check the documentation" — synthesize the information directly.
- Only say you don't know if the topic is completely absent from the context.

Media embedding rules:
- Embed images inline using: ![description](url)
- Embed videos inline using: [▶ Watch: Brief Title](video_url)
- Place media naturally after the relevant paragraph.
- Never include links ending in .md — only use full https:// URLs.
- Do not include inline hyperlinks to Adobe documentation pages in your answer. Describe topics and guide titles by name only — source links are shown automatically in the citations panel.

Retrieved documentation context:
{context}"""

_HAIKU_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _HAIKU_SYSTEM),
    MessagesPlaceholder("history"),
    ("human", "{query}"),
])

_SONNET_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _SONNET_SYSTEM),
    MessagesPlaceholder("history"),
    ("human", "{query}"),
])


# ── LCEL chains ───────────────────────────────────────────────────────────────

def _build_haiku_chain(api_key: str):
    llm = ChatAnthropic(model=_HAIKU_MODEL, api_key=api_key, max_tokens=2000, streaming=True)
    return _HAIKU_PROMPT | llm | StrOutputParser()


def _build_sonnet_chain(api_key: str):
    llm = ChatAnthropic(model=_SONNET_MODEL, api_key=api_key, max_tokens=4000, streaming=True)
    return _SONNET_PROMPT | llm | StrOutputParser()


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

    async def _emit_evidence(
        self,
        raw_docs,
        product_intent,
        failure_reason=None,
        related_docs=None,
        refinement: RefinementResult | None = None,
    ):
        ref_fields = refinement_to_evidence_fields(refinement)
        evidence = build_evidence(
            raw_docs,
            product_intent,
            failure_reason,
            related_docs,
            refinement=ref_fields or None,
        )
        sources = evidence.get("sources") or []
        if sources:
            sources = await filter_valid_citations(sources)
        evidence = {
            **evidence,
            "sources": sources,
            "source_count": len(sources),
            "citation_count": sum(1 for s in sources if s.get("cited")),
        }
        return evidence

    def _retrieve_docs(self, search_query, user_query, settings, product_intent, where_filter):
        return retrieve_with_refinement(
            self.retriever,
            search_query,
            user_query,
            n_results=settings.max_retrieval_results,
            similarity_threshold=settings.similarity_threshold,
            product_filter=product_intent,
            where_filter=where_filter,
        )

    async def _run_retrieval_path(self, query, search_query, settings, product_intent, where_filter):
        """Shared retrieval + refinement. Returns (raw_docs, refinement, blocked_reason)."""
        raw_docs, refinement = self._retrieve_docs(
            search_query, query, settings, product_intent, where_filter
        )
        if not raw_docs:
            related = self._fetch_related_docs(search_query, where_filter)
            return raw_docs, refinement, related, "no_retrieval"
        if self._is_off_topic(raw_docs):
            return raw_docs, refinement, None, "off_topic"
        return raw_docs, refinement, None, None

    # ── Haiku: single-pass LCEL chain ─────────────────────────────────────────

    async def _stream_chain(self, query, session_id, history, settings):
        enhanced, _ = self.query_processor.preprocess_query(query)
        search_query = _contextualize_query(enhanced, history)

        product_intent = detect_product_intent(query)
        where_filter = {"product": {"$eq": product_intent}} if product_intent else None

        raw_docs, refinement, related, blocked = await self._run_retrieval_path(
            query, search_query, settings, product_intent, where_filter,
        )
        if blocked == "no_retrieval":
            evidence = await self._emit_evidence([], product_intent, "no_retrieval", related, refinement)
            yield {"type": "evidence", **evidence}
            yield {"type": "token", "content": NO_CONTEXT_MESSAGE}
            yield {"type": "done", "model": "none", "session_id": session_id}
            return

        if blocked == "off_topic":
            evidence = await self._emit_evidence(raw_docs, product_intent, "off_topic", refinement=refinement)
            yield {"type": "evidence", **evidence}
            yield {"type": "token", "content": _OUT_OF_SCOPE_RESPONSE}
            self.session_store.append_turn(session_id, "user", query)
            self.session_store.append_turn(session_id, "assistant", _OUT_OF_SCOPE_RESPONSE)
            yield {"type": "citations", "citations": []}
            yield {"type": "done", "model": "none", "session_id": session_id,
                   "input_tokens": 0, "output_tokens": 0}
            return

        evidence = await self._emit_evidence(raw_docs, product_intent, refinement=refinement)
        yield {"type": "evidence", **evidence}

        # Number docs so the LLM can cite [1], [2], etc. inline
        context = "\n\n---\n\n".join(
            f"[{i+1}] {doc['content']}" for i, doc in enumerate(raw_docs)
        )
        context += _build_media_context(raw_docs)

        raw_citations = self._extract_citations(raw_docs)
        lc_history = _to_lc_history(history)
        chain = _build_haiku_chain(settings.anthropic_api_key)

        # Kick off URL validation concurrently while the LLM streams — hides latency
        import asyncio as _asyncio
        validation_task = _asyncio.create_task(filter_valid_citations(raw_citations))

        full_response = ""
        async for chunk in chain.astream({"context": context, "history": lc_history, "query": query}):
            full_response += chunk
            yield {"type": "token", "content": chunk}

        citations = await validation_task
        self.session_store.append_turn(session_id, "user", query)
        self.session_store.append_turn(session_id, "assistant", full_response)
        yield {"type": "citations", "citations": citations}
        # Estimate token counts from text lengths (÷4 chars per token)
        input_tokens = (len(_HAIKU_SYSTEM) + len(context) + len(query)
                        + sum(len(getattr(m, "content", "")) for m in lc_history)) // 4
        output_tokens = len(full_response) // 4
        yield {"type": "done", "model": "haiku", "session_id": session_id,
               "input_tokens": input_tokens, "output_tokens": output_tokens}

    # ── Sonnet: single-pass LCEL chain ───────────────────────────────────────

    async def _stream_agent(self, query, session_id, history, settings):
        enhanced, _ = self.query_processor.preprocess_query(query)
        search_query = _contextualize_query(enhanced, history)

        product_intent = detect_product_intent(query)
        where_filter = {"product": {"$eq": product_intent}} if product_intent else None

        raw_docs, refinement, related, blocked = await self._run_retrieval_path(
            query, search_query, settings, product_intent, where_filter,
        )
        if blocked == "no_retrieval":
            evidence = await self._emit_evidence([], product_intent, "no_retrieval", related, refinement)
            yield {"type": "evidence", **evidence}
            yield {"type": "token", "content": NO_CONTEXT_MESSAGE}
            yield {"type": "done", "model": "none", "session_id": session_id}
            return

        if blocked == "off_topic":
            evidence = await self._emit_evidence(raw_docs, product_intent, "off_topic", refinement=refinement)
            yield {"type": "evidence", **evidence}
            yield {"type": "token", "content": _OUT_OF_SCOPE_RESPONSE}
            self.session_store.append_turn(session_id, "user", query)
            self.session_store.append_turn(session_id, "assistant", _OUT_OF_SCOPE_RESPONSE)
            yield {"type": "citations", "citations": []}
            yield {"type": "done", "model": "none", "session_id": session_id,
                   "input_tokens": 0, "output_tokens": 0}
            return

        evidence = await self._emit_evidence(raw_docs, product_intent, refinement=refinement)
        yield {"type": "evidence", **evidence}

        context = "\n\n---\n\n".join(
            f"[{i+1}] {doc['content']}" for i, doc in enumerate(raw_docs)
        )
        context += _build_media_context(raw_docs)

        raw_citations = self._extract_citations(raw_docs)
        lc_history = _to_lc_history(history)
        chain = _build_sonnet_chain(settings.anthropic_api_key)

        import asyncio as _asyncio
        validation_task = _asyncio.create_task(filter_valid_citations(raw_citations))

        full_response = ""
        async for chunk in chain.astream({"context": context, "history": lc_history, "query": query}):
            full_response += chunk
            yield {"type": "token", "content": chunk}

        citations = await validation_task
        self.session_store.append_turn(session_id, "user", query)
        self.session_store.append_turn(session_id, "assistant", full_response)
        yield {"type": "citations", "citations": citations}
        input_tokens = (len(_SONNET_SYSTEM) + len(context) + len(query)
                        + sum(len(getattr(m, "content", "")) for m in lc_history)) // 4
        output_tokens = len(full_response) // 4
        yield {"type": "done", "model": "sonnet", "session_id": session_id,
               "input_tokens": input_tokens, "output_tokens": output_tokens}

    # ── Helpers ───────────────────────────────────────────────────────────────

    # Minimum similarity score for a doc to become a citation.
    # Docs retrieved below this threshold are used for LLM context but not shown as sources.
    _CITATION_SCORE_THRESHOLD = 0.70

    def _extract_citations(self, raw_docs: list) -> list:
        """Extract citations from ChromaDB metadata, deduplicated by URL."""
        seen_urls: set = set()
        citations = []
        for doc in raw_docs:
            score = doc.get("score", 0.0)
            if score < self._CITATION_SCORE_THRESHOLD:
                continue
            meta = doc.get("metadata", {})
            url = resolve_doc_url(meta, doc.get("content", "")) or meta.get("url", "")
            if not is_specific_url(url):
                continue
            if url in seen_urls:
                continue
            seen_urls.add(url)
            # Strip AdobeDocs anchor syntax from titles e.g. "Accessibility {#accessibility}"
            raw_title = meta.get("title", "")
            title = re.sub(r"\s*\{#[^}]+\}", "", raw_title).strip()
            c: dict = {
                "url": url,
                "title": title,
                "product": meta.get("product", ""),
                "score": score,
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

    def _fetch_related_docs(self, search_query: str, where_filter: dict | None) -> list:
        """Lower-threshold retrieval for evidence display on blocked responses only."""
        return self.retriever.retrieve(
            search_query,
            n_results=5,
            similarity_threshold=0.0,
            where=where_filter,
        )
