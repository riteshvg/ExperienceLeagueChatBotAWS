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

from backend.core.llm_factory import get_chat_model, get_messages_client
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

_PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.core.chroma_retriever import ChromaRetriever
from backend.core.evidence import build_evidence
from backend.core.groundedness import (
    extract_known_urls,
    pseudo_chunk,
    resolve_with_escalation,
    run_groundedness_check,
    should_run_groundedness_check,
)
from backend.core.retrieval_refiner import (
    RefinementResult,
    refinement_to_evidence_fields,
    retrieve_with_refinement,
)
from backend.core.topical_relevance import (
    _MIN_SIGNIFICANT_FOR_URL_CHECK,
    assess_retrieval,
    significant_terms,
    topical_match_score,
)
from backend.core.session_store import SessionStore
from backend.core.smart_router import classify_query, detect_product_intent
from backend.core.url_validator import filter_valid_citations
from config.prompts import NO_CONTEXT_MESSAGE, NO_DIRECT_MATCH_MESSAGE
from config.settings import get_settings
from backend.core.query_processor import QueryProcessor
from src.utils.exl_url_mapper import is_specific_url, resolve_doc_url

logger = logging.getLogger(__name__)

# Embedding-similarity rescue for the topical gate — a query can score below the
# lexical topical threshold on vocabulary mismatch alone (business/compliance
# paraphrase vs. doc terminology) while still being a real match. Stress-test:
# genuine matches wrongly blocked scored 0.353-0.644; genuinely off-topic queries
# capped out at 0.125-0.214 — clean separation, so this only rescues real matches.
_EMBED_RESCUE_THRESHOLD = 0.35

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

Before answering, check the retrieved documentation context below.
- If the context contains information that addresses the question, answer using it — even if \
the question's wording doesn't obviously name an Adobe product. The retrieval system has already \
confirmed this context is relevant; do not re-judge topic relevance from the question's surface \
phrasing alone.
- If the context partially addresses the question, answer with what's supported and explicitly \
note what's missing — don't treat it as all-or-nothing.
- If the context does NOT address the question (empty, or unrelated to what was asked), say so \
plainly: "I don't have information on this in Adobe Experience League documentation." Never \
speculate about what the user might have meant as an alternative to answering — if you're unsure \
whether the context addresses the question, say what the context does cover and ask a clarifying \
question instead of guessing.
- Only use the "I can only answer questions about Adobe Analytics, CJA, AEP, Adobe Target, Adobe \
Journey Optimizer, and Adobe Data Collection" response if there is no retrieved context at all for \
this turn.

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

Before answering, check the retrieved documentation context below.
- If the context contains information that addresses the question, answer using it — even if \
the question's wording doesn't obviously name an Adobe product. The retrieval system has already \
confirmed this context is relevant; do not re-judge topic relevance from the question's surface \
phrasing alone.
- If the context partially addresses the question, answer with what's supported and explicitly \
note what's missing — don't treat it as all-or-nothing.
- If the context does NOT address the question (empty, or unrelated to what was asked), say so \
plainly: "I don't have information on this in Adobe Experience League documentation." Never \
speculate about what the user might have meant as an alternative to answering — if you're unsure \
whether the context addresses the question, say what the context does cover and ask a clarifying \
question instead of guessing.
- Only use the "I can only answer questions about Adobe Analytics, CJA, AEP, Adobe Target, Adobe \
Journey Optimizer, and Adobe Data Collection" response if there is no retrieved context at all for \
this turn.

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

def _build_haiku_chain(settings, max_tokens: int = 2000):
    llm = get_chat_model("haiku", settings, max_tokens)
    return _HAIKU_PROMPT | llm | StrOutputParser()


def _build_sonnet_chain(settings, max_tokens: int = 4000):
    llm = get_chat_model("sonnet", settings, max_tokens)
    return _SONNET_PROMPT | llm | StrOutputParser()


# Tail-latency safety net for the admin-only groundedness-check path: real
# output lengths are almost always well under this (median ~712 tokens, p90
# ~1024 across the golden set — see eval/full_pipeline_rerun_v2.json), so this
# rarely binds. It exists to bound the rare very-long-generation outliers,
# which also correlate with higher fabrication risk (more room to invent
# specifics), not to speed up the typical case.
_ADMIN_TRIGGERED_HAIKU_MAX_TOKENS = 1200
_ADMIN_TRIGGERED_SONNET_MAX_TOKENS = 1400


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
        user_email: str | None = None,
    ) -> AsyncGenerator[dict, None]:
        try:
            yield {"type": "status", "stage": "understanding"}

            settings = get_settings()
            history = self.session_store.get_history(session_id)

            # Route: haiku_only flag overrides auto-routing
            routed = "haiku" if haiku_only else classify_query(query)
            logger.info(f"SmartRouter: '{query[:60]}' → {routed}")

            if routed == "sonnet":
                async for event in self._stream_agent(query, session_id, history, settings, user_email):
                    yield event
            else:
                async for event in self._stream_chain(query, session_id, history, settings, user_email):
                    yield event

        except Exception as exc:
            logger.exception("RAG pipeline error")
            yield {"type": "error", "message": str(exc)}

    def _is_admin_request(self, user_email: str | None) -> bool:
        """Gate for the admin-only groundedness-check rollout — reuses the same
        ADMIN_EMAIL identity mechanism as backend/api/deps.py:get_admin_user()
        and backend/core/google_db.py, rather than introducing a new one.
        Empty/unset ADMIN_EMAIL or user_email always returns False (fail closed
        — no accidental opt-in for everyone if the env var is missing)."""
        admin_email = (get_settings().admin_email or "").strip().lower()
        return bool(admin_email) and bool(user_email) and user_email.strip().lower() == admin_email

    async def _emit_evidence(
        self,
        raw_docs,
        product_intent,
        failure_reason=None,
        related_docs=None,
        refinement: RefinementResult | None = None,
        topical_scores: dict | None = None,
    ):
        ref_fields = refinement_to_evidence_fields(refinement)
        evidence = build_evidence(
            raw_docs,
            product_intent,
            failure_reason,
            related_docs,
            refinement=ref_fields or None,
            topical_scores=topical_scores,
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

    async def _run_retrieval_path(
        self,
        query,
        search_query,
        settings,
        product_intent,
        where_filter,
    ):
        """Shared retrieval + refinement + topical gate."""
        raw_docs, refinement = self._retrieve_docs(
            search_query, query, settings, product_intent, where_filter
        )
        assessment = assess_retrieval(query, raw_docs, product_intent)
        relevant_docs = assessment["relevant_docs"]
        product_docs = assessment["product_docs"]
        topical_scores = assessment["topical_scores"]

        if not raw_docs:
            related = self._fetch_related_docs(search_query, where_filter)
            return [], refinement, related, topical_scores, "no_retrieval"

        if not relevant_docs and product_intent and where_filter:
            # A hard product where-clause can exclude the doc that actually
            # answers a cross-product concept (e.g. "identityMap" is a shared
            # Data-Collection/XDM field, not AJO-specific, so an AJO-only pool
            # never contains it even when AJO-scoped retrieval otherwise looks
            # healthy). Retry once, unscoped, before giving up — the topical
            # gate below still applies in full (assess_retrieval runs its
            # normal, unrelaxed substring/URL check when product_filter is
            # None), so this only widens the candidate pool, not the gate's
            # precision bar.
            unscoped_docs, unscoped_refinement = self._retrieve_docs(
                search_query, query, settings, None, None,
            )
            unscoped_assessment = assess_retrieval(query, unscoped_docs, None)
            if unscoped_assessment["relevant_docs"]:
                raw_docs = unscoped_docs
                refinement = unscoped_refinement
                relevant_docs = unscoped_assessment["relevant_docs"]
                product_docs = unscoped_assessment["product_docs"]
                topical_scores = unscoped_assessment["topical_scores"]

        if not relevant_docs:
            # Pure-lexical topical gate found nothing, but a strong embedding match
            # can still indicate a real answer the lexical gate missed on vocabulary
            # (paraphrase/synonym mismatch between query wording and doc wording —
            # see rag_pipeline investigation, stress-test showed off-topic queries
            # cap out well below this threshold while genuine paraphrased matches
            # sit above it). Rescue pool is product-scoped when a product filter
            # was applied, otherwise the full raw retrieval pool.
            rescue_pool = product_docs if product_intent else raw_docs
            embed_rescued = [
                d for d in rescue_pool
                if float(d.get("score", 0.0)) >= _EMBED_RESCUE_THRESHOLD
            ]
            if embed_rescued:
                relevant_docs = sorted(
                    embed_rescued, key=lambda d: float(d.get("score", 0.0)), reverse=True,
                )
            else:
                related = product_docs or self._fetch_related_docs(search_query, where_filter)
                related = sorted(related, key=lambda d: float(d.get("score", 0.0)), reverse=True)[:3]
                related_scores = {
                    (d.get("metadata") or {}).get("s3_key")
                    or (d.get("metadata") or {}).get("url")
                    or d.get("content", "")[:80]: 0.0
                    for d in related
                }
                topical_scores = {**topical_scores, **related_scores}
                return [], refinement, related, topical_scores, "no_direct_match"

        # Weak topical alignment — treat as no direct match rather than a low-confidence
        # answer, unless a strong embedding match rescues it (same rationale as above).
        # Skipped when product_intent already hard-scoped retrieval (a real Chroma
        # where-clause) and too few significant terms survive to be a meaningful
        # lexical signal — same condition as assess_retrieval's gate relaxation.
        best_topical = max(topical_match_score(query, d) for d in relevant_docs)
        best_embed = max(float(d.get("score", 0.0)) for d in relevant_docs)
        thin_significant_terms = len(significant_terms(query)) < _MIN_SIGNIFICANT_FOR_URL_CHECK
        if (
            best_topical < 0.22
            and best_embed < _EMBED_RESCUE_THRESHOLD
            and not (product_intent and thin_significant_terms)
        ):
            related = sorted(
                relevant_docs + (product_docs or []),
                key=lambda d: float(d.get("score", 0.0)),
                reverse=True,
            )[:5]
            return [], refinement, related, topical_scores, "no_direct_match"

        if self._is_off_topic(relevant_docs):
            # API-product queries often retrieve real docs with weak embedding
            # scores (terse reference content vs. a conversational query), so a
            # bare off-topic block would wrongly drop them. The bypass is gated
            # on topical_match_score, not on the product name alone — "api"/
            # "apis" are generic terms (see topical_relevance._GENERIC_TERMS),
            # so this score reflects real shared vocabulary, not just the
            # product's own name appearing in the query. Empirically, off-topic
            # queries that merely namedrop an API product cap out at ~0.23;
            # genuine matches clear 0.30 with margin (see test_rag_pipeline.py).
            best_topical = max(topical_match_score(query, d) for d in relevant_docs)
            if not (
                product_intent
                and product_intent.endswith(" APIs")
                and best_topical >= 0.30
            ):
                return relevant_docs, refinement, None, topical_scores, "off_topic"

        return relevant_docs, refinement, None, topical_scores, None

    def _resolve_retrieval_inputs(
        self,
        query: str,
        history: list[dict],
    ) -> tuple[str, str, str | None, dict | None]:
        """Return (query, search_query, product_intent, where_filter)."""
        enhanced, _ = self.query_processor.preprocess_query(query)
        search_query = _contextualize_query(enhanced, history)
        product_intent = detect_product_intent(query)
        where_filter = {"product": {"$eq": product_intent}} if product_intent else None
        return query, search_query, product_intent, where_filter

    async def _emit_block(
        self,
        product_intent,
        blocked,
        related,
        refinement,
        topical_scores,
        session_id,
    ):
        """Yield the hard-block fallback response for a blocked retrieval outcome."""
        if blocked == "no_retrieval":
            evidence = await self._emit_evidence(
                [], product_intent, "no_retrieval", related, refinement, topical_scores,
            )
            yield {"type": "evidence", **evidence}
            yield {"type": "token", "content": NO_CONTEXT_MESSAGE}
            yield {"type": "done", "model": "none", "session_id": session_id}
            return

        evidence = await self._emit_evidence(
            [], product_intent, "no_direct_match", related, refinement, topical_scores,
        )
        yield {"type": "evidence", **evidence}
        yield {"type": "token", "content": NO_DIRECT_MATCH_MESSAGE}
        yield {"type": "done", "model": "none", "session_id": session_id}

    # ── Haiku: single-pass LCEL chain ─────────────────────────────────────────

    async def _stream_chain(self, query, session_id, history, settings, user_email=None):
        query_to_use, search_query, product_intent, where_filter = (
            self._resolve_retrieval_inputs(query, history)
        )
        is_admin = self._is_admin_request(user_email)

        if is_admin:
            yield {"type": "status", "stage": "searching", "message": "Looking through Adobe's documentation…"}
        else:
            yield {"type": "status", "stage": "searching"}

        raw_docs, refinement, related, topical_scores, blocked = await self._run_retrieval_path(
            query_to_use, search_query, settings, product_intent, where_filter,
        )
        if blocked == "no_retrieval" or blocked == "no_direct_match":
            async for event in self._emit_block(
                product_intent,
                blocked,
                related,
                refinement,
                topical_scores,
                session_id,
            ):
                yield event
            return

        if blocked == "off_topic":
            evidence = await self._emit_evidence(
                raw_docs, product_intent, "off_topic", refinement=refinement, topical_scores=topical_scores,
            )
            yield {"type": "evidence", **evidence}
            yield {"type": "token", "content": _OUT_OF_SCOPE_RESPONSE}
            self.session_store.append_turn(session_id, "user", query_to_use)
            self.session_store.append_turn(session_id, "assistant", _OUT_OF_SCOPE_RESPONSE)
            yield {"type": "citations", "citations": []}
            yield {"type": "done", "model": "none", "session_id": session_id,
                   "input_tokens": 0, "output_tokens": 0}
            return

        evidence = await self._emit_evidence(
            raw_docs, product_intent, refinement=refinement, topical_scores=topical_scores,
        )
        yield {"type": "evidence", **evidence}

        # Number docs so the LLM can cite [1], [2], etc. inline
        context = "\n\n---\n\n".join(
            f"[{i+1}] {doc['content']}" for i, doc in enumerate(raw_docs)
        )
        context += _build_media_context(raw_docs)
        yield {"type": "context", "context": context}

        raw_citations = self._extract_citations(raw_docs)
        lc_history = _to_lc_history(history)

        admin_triggered = is_admin and should_run_groundedness_check(evidence)
        chain = (
            _build_haiku_chain(settings, max_tokens=_ADMIN_TRIGGERED_HAIKU_MAX_TOKENS)
            if admin_triggered
            else _build_haiku_chain(settings)
        )

        # Kick off URL validation concurrently while the LLM streams — hides latency
        import asyncio as _asyncio
        validation_task = _asyncio.create_task(filter_valid_citations(raw_citations))

        if is_admin:
            yield {"type": "status", "stage": "writing", "message": "Drafting your answer…"}
        else:
            yield {"type": "status", "stage": "writing"}

        full_response = ""
        if admin_triggered:
            async for chunk in chain.astream({"context": context, "history": lc_history, "query": query_to_use}):
                full_response += chunk
            yield {
                "type": "status", "stage": "reviewing",
                "message": "Double-checking this against the source docs before showing it to you…",
            }
            groundedness_task = _asyncio.create_task(
                self._apply_groundedness_ux(settings, query_to_use, full_response, context, evidence)
            )
            done, pending = await _asyncio.wait({groundedness_task}, timeout=15)
            if pending:
                yield {
                    "type": "status", "stage": "still_reviewing",
                    "message": "Making sure every detail here is actually documented, not just plausible…",
                }
            resolved = await groundedness_task
            full_response = resolved["final_answer"]
            yield {"type": "groundedness", "ux_action": resolved["ux_action"], "escalated": resolved["escalated"]}
            for piece in pseudo_chunk(full_response):
                yield {"type": "token", "content": piece}
        else:
            async for chunk in chain.astream({"context": context, "history": lc_history, "query": query_to_use}):
                full_response += chunk
                yield {"type": "token", "content": chunk}

        citations = await validation_task
        self.session_store.append_turn(session_id, "user", query_to_use)
        self.session_store.append_turn(session_id, "assistant", full_response)
        yield {"type": "citations", "citations": citations}
        # Estimate token counts from text lengths (÷4 chars per token)
        input_tokens = (len(_HAIKU_SYSTEM) + len(context) + len(query_to_use)
                        + sum(len(getattr(m, "content", "")) for m in lc_history)) // 4
        output_tokens = len(full_response) // 4
        yield {"type": "done", "model": "haiku", "session_id": session_id,
               "input_tokens": input_tokens, "output_tokens": output_tokens}

    # ── Sonnet: single-pass LCEL chain ───────────────────────────────────────

    async def _stream_agent(self, query, session_id, history, settings, user_email=None):
        query_to_use, search_query, product_intent, where_filter = (
            self._resolve_retrieval_inputs(query, history)
        )
        is_admin = self._is_admin_request(user_email)

        if is_admin:
            yield {"type": "status", "stage": "searching", "message": "Looking through Adobe's documentation…"}
        else:
            yield {"type": "status", "stage": "searching"}

        raw_docs, refinement, related, topical_scores, blocked = await self._run_retrieval_path(
            query_to_use, search_query, settings, product_intent, where_filter,
        )
        if blocked == "no_retrieval" or blocked == "no_direct_match":
            async for event in self._emit_block(
                product_intent,
                blocked,
                related,
                refinement,
                topical_scores,
                session_id,
            ):
                yield event
            return

        if blocked == "off_topic":
            evidence = await self._emit_evidence(
                raw_docs, product_intent, "off_topic", refinement=refinement, topical_scores=topical_scores,
            )
            yield {"type": "evidence", **evidence}
            yield {"type": "token", "content": _OUT_OF_SCOPE_RESPONSE}
            self.session_store.append_turn(session_id, "user", query_to_use)
            self.session_store.append_turn(session_id, "assistant", _OUT_OF_SCOPE_RESPONSE)
            yield {"type": "citations", "citations": []}
            yield {"type": "done", "model": "none", "session_id": session_id,
                   "input_tokens": 0, "output_tokens": 0}
            return

        evidence = await self._emit_evidence(
            raw_docs, product_intent, refinement=refinement, topical_scores=topical_scores,
        )
        yield {"type": "evidence", **evidence}

        context = "\n\n---\n\n".join(
            f"[{i+1}] {doc['content']}" for i, doc in enumerate(raw_docs)
        )
        context += _build_media_context(raw_docs)
        yield {"type": "context", "context": context}

        raw_citations = self._extract_citations(raw_docs)
        lc_history = _to_lc_history(history)

        admin_triggered = is_admin and should_run_groundedness_check(evidence)
        chain = (
            _build_sonnet_chain(settings, max_tokens=_ADMIN_TRIGGERED_SONNET_MAX_TOKENS)
            if admin_triggered
            else _build_sonnet_chain(settings)
        )

        import asyncio as _asyncio
        validation_task = _asyncio.create_task(filter_valid_citations(raw_citations))

        if is_admin:
            yield {"type": "status", "stage": "writing", "message": "Drafting your answer…"}
        else:
            yield {"type": "status", "stage": "writing"}

        full_response = ""
        if admin_triggered:
            async for chunk in chain.astream({"context": context, "history": lc_history, "query": query_to_use}):
                full_response += chunk
            yield {
                "type": "status", "stage": "reviewing",
                "message": "Double-checking this against the source docs before showing it to you…",
            }
            groundedness_task = _asyncio.create_task(
                self._apply_groundedness_ux(settings, query_to_use, full_response, context, evidence)
            )
            done, pending = await _asyncio.wait({groundedness_task}, timeout=15)
            if pending:
                yield {
                    "type": "status", "stage": "still_reviewing",
                    "message": "Making sure every detail here is actually documented, not just plausible…",
                }
            resolved = await groundedness_task
            full_response = resolved["final_answer"]
            yield {"type": "groundedness", "ux_action": resolved["ux_action"], "escalated": resolved["escalated"]}
            for piece in pseudo_chunk(full_response):
                yield {"type": "token", "content": piece}
        else:
            async for chunk in chain.astream({"context": context, "history": lc_history, "query": query_to_use}):
                full_response += chunk
                yield {"type": "token", "content": chunk}

        citations = await validation_task
        self.session_store.append_turn(session_id, "user", query_to_use)
        self.session_store.append_turn(session_id, "assistant", full_response)
        yield {"type": "citations", "citations": citations}
        input_tokens = (len(_SONNET_SYSTEM) + len(context) + len(query_to_use)
                        + sum(len(getattr(m, "content", "")) for m in lc_history)) // 4
        output_tokens = len(full_response) // 4
        yield {"type": "done", "model": "sonnet", "session_id": session_id,
               "input_tokens": input_tokens, "output_tokens": output_tokens}

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _apply_groundedness_ux(
        self, settings, query: str, answer: str, context: str, evidence: dict,
    ) -> dict:
        """Buffered-path post-processing: check the complete answer against its
        context, and if it fabricates specifics, surgically remove or replace
        the response before any of it reaches the client. Only called when
        should_run_groundedness_check(evidence) is True (see call sites).

        Returns the full resolve_with_escalation() dict (final_answer, ux_action,
        escalated, reverify_chain) — callers that only need the text should read
        result["final_answer"]. Exposing the full dict lets callers (production
        SSE stream, eval harness) observe what the check actually decided instead
        of having to re-run it, which would trivially find nothing wrong since
        the answer is already post-UX-layer."""
        client = get_messages_client(settings)
        known_urls = extract_known_urls(evidence)
        check_result = await run_groundedness_check(client, context, answer, known_urls=known_urls)
        return await resolve_with_escalation(client, query, answer, context, evidence, check_result)

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
