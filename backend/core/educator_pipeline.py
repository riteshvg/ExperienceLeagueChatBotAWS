"""
Educator Mode v2 pipeline — Socratic teaching with doc-grounded verification.
"""

from __future__ import annotations

import logging
from typing import Any, AsyncGenerator

from anthropic import AsyncAnthropic

from backend.core.chroma_retriever import ChromaRetriever
from backend.core.domain_selector import select_next_domain
from backend.core.educator_prompt import build_educator_system_prompt
from backend.core.query_processor import QueryProcessor
from backend.core.session_store import SessionStore
from config.exams import get_exam
from config.settings import get_settings

logger = logging.getLogger(__name__)

_MODEL = "claude-sonnet-4-6"
_MAX_TOKENS = 1500
_MAX_TOOL_ROUNDS = 5

_SEARCH_TOOL = {
    "name": "search_experience_league",
    "description": (
        "Search Adobe Experience League documentation. Use to verify answers and to surface "
        "doc sections when the candidate requests them before attempting."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Specific concept or feature to look up",
            }
        },
        "required": ["query"],
    },
}


class EducatorPipeline:
    def __init__(self, retriever: ChromaRetriever, session_store: SessionStore):
        self.retriever = retriever
        self.session_store = session_store
        self.query_processor = QueryProcessor()

    def _search_docs(self, query: str) -> str:
        enhanced, _ = self.query_processor.preprocess_query(query)
        settings = get_settings()
        docs = self.retriever.retrieve(
            enhanced,
            n_results=5,
            similarity_threshold=max(0.2, settings.similarity_threshold * 0.7),
        )
        if not docs:
            return f"No documentation found for: {query}"

        parts = []
        for i, doc in enumerate(docs, 1):
            meta = doc.get("metadata", {})
            url = meta.get("url", "")
            title = meta.get("title", f"Document {i}")
            product = meta.get("product", "")
            header = f"[{i}] {title}"
            if product:
                header += f" ({product})"
            if url:
                header += f"\nSource: {url}"
            parts.append(f"{header}\n\n{doc['content'][:700]}")

        return "\n\n---\n\n".join(parts)

    async def stream(
        self,
        messages: list[dict],
        exam_id: str,
        domain_scores: dict[str, dict[str, int]],
        session_id: str,
        question_number: int = 1,
        current_question: dict[str, Any] | None = None,
        active_domain_id: str | None = None,
    ) -> AsyncGenerator[dict, None]:
        exam = get_exam(exam_id)
        if not exam:
            yield {"type": "error", "message": f"Unknown exam ID: {exam_id}"}
            return

        settings = get_settings()
        if not settings.anthropic_api_key:
            yield {"type": "error", "message": "Anthropic API key not configured."}
            return

        next_domain = select_next_domain(exam, domain_scores)
        if active_domain_id:
            for d in exam.domains:
                if d.id == active_domain_id:
                    next_domain = d
                    break

        system_prompt = build_educator_system_prompt(exam, next_domain)
        attempt_count = len((current_question or {}).get("attempts", []))

        augmented = [dict(m) for m in messages]
        if augmented and augmented[-1].get("role") == "user":
            ctx = (
                f"\n\n[INTERNAL CONTEXT — do not surface to candidate: "
                f'Domain: "{next_domain.name}". '
                f'Doc search hint: "{next_domain.doc_search_hint}". '
                f"Question number: {question_number}. "
                f"Attempts on current question: {attempt_count}.]"
            )
            augmented[-1]["content"] = augmented[-1]["content"] + ctx

        client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        api_messages = [{"role": m["role"], "content": m["content"]} for m in augmented]

        try:
            full_response = ""
            for _ in range(_MAX_TOOL_ROUNDS):
                response = await client.messages.create(
                    model=_MODEL,
                    max_tokens=_MAX_TOKENS,
                    system=system_prompt,
                    messages=api_messages,
                    tools=[_SEARCH_TOOL],
                )

                tool_uses = [b for b in response.content if b.type == "tool_use"]
                text_blocks = [b.text for b in response.content if b.type == "text"]
                round_text = "".join(text_blocks)

                if not tool_uses:
                    full_response = round_text
                    break

                api_messages.append({"role": "assistant", "content": response.content})

                tool_results = []
                for tool_use in tool_uses:
                    if tool_use.name == "search_experience_league":
                        result = self._search_docs(tool_use.input.get("query", ""))
                    else:
                        result = f"Unknown tool: {tool_use.name}"
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": result,
                        }
                    )

                api_messages.append({"role": "user", "content": tool_results})

                if response.stop_reason == "end_turn" and round_text:
                    full_response = round_text

            if not full_response:
                final = await client.messages.create(
                    model=_MODEL,
                    max_tokens=_MAX_TOKENS,
                    system=system_prompt,
                    messages=api_messages,
                )
                full_response = "".join(
                    b.text for b in final.content if b.type == "text"
                )

            words = full_response.split(" ")
            for i, word in enumerate(words):
                chunk = word + (" " if i < len(words) - 1 else "")
                yield {"type": "token", "content": chunk}

            last_user = next(
                (m["content"] for m in reversed(augmented) if m["role"] == "user"),
                "",
            )
            self.session_store.append_turn(session_id, "user", last_user)
            self.session_store.append_turn(session_id, "assistant", full_response)

            yield {
                "type": "done",
                "model": "educator",
                "session_id": session_id,
                "active_domain": next_domain.id,
                "next_domain": next_domain.id,
                "next_domain_name": next_domain.name,
            }

        except Exception as exc:
            logger.exception("Educator pipeline error")
            yield {"type": "error", "message": str(exc)}
