"""
Interviewer Mode pipeline — session management, question delivery, deferred evaluation.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Literal

from anthropic import AsyncAnthropic

from backend.core.chroma_retriever import ChromaRetriever
from backend.core.interviewer_prompt import (
    build_evaluation_user_prompt,
    build_interviewer_system_prompt,
    build_session_evaluation_prompt,
    build_welcome_message,
)
from backend.core.query_processor import QueryProcessor
from backend.core.retrieval_refiner import retrieve_with_refinement
from backend.core.smart_router import detect_product_intent
from config.interview_profiles import InterviewQuestion, get_question_set, profile_label
from config.settings import get_settings

logger = logging.getLogger(__name__)

_MODEL = "claude-sonnet-4-6"
SessionPhase = Literal["questioning", "review", "complete"]
_sessions: dict[str, "InterviewSession"] = {}


@dataclass
class InterviewSession:
    session_id: str
    user_id: str
    level: str
    profile_id: str
    questions: list[InterviewQuestion]
    current_index: int = 0
    phase: SessionPhase = "questioning"
    awaiting_advance: bool = False
    draft_answers: dict[str, str] = field(default_factory=dict)
    evaluated: bool = False
    per_question_results: list[dict[str, Any]] = field(default_factory=list)
    session_report: dict[str, Any] | None = None

    @property
    def total(self) -> int:
        return len(self.questions)

    @property
    def completed(self) -> bool:
        return self.phase == "complete"

    def current_question(self) -> InterviewQuestion | None:
        if self.phase != "questioning" or self.current_index >= len(self.questions):
            return None
        return self.questions[self.current_index]

    def save_current_answer(self, answer: str) -> dict[str, Any]:
        if self.phase != "questioning":
            raise ValueError("Session is not accepting answers.")
        q = self.current_question()
        if not q:
            raise ValueError("No active question in this session.")
        text = answer.strip()
        if not text:
            raise ValueError("Please provide an answer before saving.")
        self.draft_answers[q.id] = text
        self.awaiting_advance = True
        is_last = self.current_index >= self.total - 1
        return {
            "question_id": q.id,
            "question_index": self.current_index + 1,
            "total_questions": self.total,
            "is_last": is_last,
            "answer": text,
        }

    def update_answer(self, question_id: str, answer: str) -> dict[str, Any]:
        text = answer.strip()
        if not text:
            raise ValueError("Answer cannot be empty.")
        known = {q.id for q in self.questions}
        if question_id not in known:
            raise ValueError(f"Unknown question: {question_id}")
        if self.phase == "questioning":
            q = self.current_question()
            if q and q.id != question_id:
                raise ValueError("Can only edit the current question before advancing.")
        self.draft_answers[question_id] = text
        idx = next(i for i, q in enumerate(self.questions) if q.id == question_id)
        return {
            "question_id": question_id,
            "question_index": idx + 1,
            "answer": text,
        }

    def advance(self) -> dict[str, Any]:
        if self.phase == "complete":
            raise ValueError("Session already completed.")
        if self.phase == "review":
            raise ValueError("Already in review — submit for evaluation when ready.")
        if not self.awaiting_advance:
            raise ValueError("Save an answer before moving to the next question.")
        self.awaiting_advance = False
        is_last = self.current_index >= self.total - 1
        if is_last:
            self.phase = "review"
            return {"phase": "review", "review_ready": True}
        self.current_index += 1
        q = self.current_question()
        return {
            "phase": "questioning",
            "current_index": self.current_index,
            "current_question": _question_to_dict(q, self.current_index, self.total) if q else None,
        }

    def get_review_items(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for i, q in enumerate(self.questions):
            items.append({
                "question": _question_to_dict(q, i, self.total),
                "answer": self.draft_answers.get(q.id, ""),
            })
        return items

    def all_answered(self) -> bool:
        return all(self.draft_answers.get(q.id, "").strip() for q in self.questions)

    def to_dict(self) -> dict[str, Any]:
        q = self.current_question()
        return {
            "session_id": self.session_id,
            "level": self.level,
            "profile_id": self.profile_id,
            "profile_label": profile_label(self.level, self.profile_id),
            "current_index": self.current_index,
            "total_questions": self.total,
            "phase": self.phase,
            "awaiting_advance": self.awaiting_advance,
            "completed": self.completed,
            "evaluated": self.evaluated,
            "current_question": _question_to_dict(q, self.current_index, self.total) if q else None,
        }


def _question_to_dict(q: InterviewQuestion, index: int, total: int) -> dict[str, Any]:
    return {
        "id": q.id,
        "question": q.question,
        "topic": q.topic,
        "difficulty": q.difficulty,
        "expected_themes": list(q.expected_themes),
        "index": index + 1,
        "total": total,
    }


def _question_event(q: InterviewQuestion, index: int, total: int) -> dict[str, Any]:
    return {"type": "question", "question": _question_to_dict(q, index, total)}


def create_session(user_id: str, level: str, profile_id: str) -> InterviewSession:
    questions = get_question_set(level, profile_id)
    session_id = str(uuid.uuid4())
    session = InterviewSession(
        session_id=session_id,
        user_id=user_id,
        level=level,
        profile_id=profile_id,
        questions=questions,
    )
    _sessions[session_id] = session
    return session


def get_session(session_id: str) -> InterviewSession | None:
    return _sessions.get(session_id)


def _product_filter(profile_id: str) -> str | None:
    mapping = {
        "cja": "Customer Journey Analytics",
        "aep": "Adobe Experience Platform",
        "web_sdk": "Adobe Data Collection",
        "target": "Adobe Target",
    }
    return mapping.get(profile_id)


def _build_doc_context(docs: list[dict]) -> str:
    if not docs:
        return "(No documentation retrieved — evaluate from general Adobe product knowledge.)"
    parts: list[str] = []
    for i, doc in enumerate(docs[:6], 1):
        meta = doc.get("metadata") or {}
        title = meta.get("title") or meta.get("source") or f"Doc {i}"
        content = (doc.get("content") or doc.get("page_content") or "")[:1200]
        parts.append(f"### [{i}] {title}\n{content}")
    return "\n\n".join(parts)


def _docs_to_citations(docs: list[dict]) -> list[dict[str, Any]]:
    citations: list[dict[str, Any]] = []
    seen: set[str] = set()
    for doc in docs[:5]:
        meta = doc.get("metadata") or {}
        url = meta.get("url") or meta.get("source_url") or ""
        if not url or url in seen:
            continue
        seen.add(url)
        citations.append({
            "url": url,
            "title": meta.get("title") or url,
            "product": meta.get("product"),
            "score": doc.get("score"),
        })
    return citations


def _parse_evaluation_json(text: str) -> dict[str, Any]:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    return {
        "score": 3,
        "score_pct": 60,
        "strengths": [],
        "gaps": ["Could not parse structured evaluation."],
        "model_answer_outline": "",
        "feedback": text,
    }


def _parse_session_report_json(text: str) -> dict[str, Any]:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    return {
        "overall_score": 3,
        "readiness": "needs_work",
        "readiness_summary": "Review the per-question feedback below.",
        "strengths": [],
        "priority_gaps": [],
        "mistakes_to_avoid": [],
        "topics_to_read": [],
        "overall_feedback": text,
    }


class InterviewerPipeline:
    def __init__(self, retriever: ChromaRetriever | None):
        self.retriever = retriever
        self._processor = QueryProcessor()
        settings = get_settings()
        self._client = AsyncAnthropic(api_key=settings.anthropic_api_key) if settings.anthropic_api_key else None

    async def stream_start(self, session: InterviewSession) -> AsyncGenerator[dict[str, Any], None]:
        welcome = build_welcome_message(session.level, session.profile_id, session.total)
        for chunk in _chunk_text(welcome):
            yield {"type": "token", "content": chunk}

        q = session.current_question()
        if q:
            yield _question_event(q, session.current_index, session.total)

        yield {
            "type": "done",
            "model": "interviewer",
            "session_id": session.session_id,
            **session.to_dict(),
        }

    async def _retrieve_for_question(self, q: InterviewQuestion, session: InterviewSession) -> list[dict]:
        if not self.retriever:
            return []
        search_query = f"{q.retrieval_hint} {q.topic}"
        product = _product_filter(session.profile_id) or detect_product_intent(search_query)
        settings = get_settings()
        try:
            enhanced, _ = self._processor.preprocess_query(search_query)
            docs, _ = retrieve_with_refinement(
                self.retriever,
                enhanced,
                search_query,
                n_results=settings.max_retrieval_results,
                similarity_threshold=settings.similarity_threshold,
                product_filter=product,
                where_filter=None,
            )
            return docs
        except Exception as exc:
            logger.warning("Interviewer retrieval failed: %s", exc)
            return []

    async def _evaluate_single(
        self,
        session: InterviewSession,
        q: InterviewQuestion,
        answer: str,
        docs: list[dict],
    ) -> dict[str, Any]:
        doc_context = _build_doc_context(docs)
        citations = _docs_to_citations(docs)

        if self._client:
            try:
                system = build_interviewer_system_prompt(session.level, session.profile_id)  # type: ignore[arg-type]
                user_prompt = build_evaluation_user_prompt(
                    question=q.question,
                    topic=q.topic,
                    expected_themes=q.expected_themes,
                    level=session.level,
                    candidate_answer=answer,
                    doc_context=doc_context,
                )
                resp = await self._client.messages.create(
                    model=_MODEL,
                    max_tokens=1200,
                    system=system,
                    messages=[{"role": "user", "content": user_prompt}],
                )
                raw = resp.content[0].text if resp.content else "{}"
                evaluation = _parse_evaluation_json(raw)
            except Exception as exc:
                logger.error("Interviewer per-question eval failed: %s", exc)
                evaluation = {
                    "score": 3,
                    "score_pct": 60,
                    "strengths": [],
                    "gaps": ["Evaluation service temporarily unavailable."],
                    "model_answer_outline": "",
                    "feedback": "",
                }
        else:
            evaluation = {
                "score": 3,
                "score_pct": 60,
                "strengths": ["Answer recorded."],
                "gaps": ["LLM evaluation unavailable — set ANTHROPIC_API_KEY."],
                "model_answer_outline": " · ".join(q.expected_themes),
                "feedback": "",
            }

        return {
            "question_id": q.id,
            "question_index": next(i for i, x in enumerate(session.questions) if x.id == q.id) + 1,
            "question": q.question,
            "topic": q.topic,
            "answer": answer,
            "score": int(evaluation.get("score", 3)),
            "score_pct": int(evaluation.get("score_pct", 60)),
            "strengths": evaluation.get("strengths") or [],
            "gaps": evaluation.get("gaps") or [],
            "model_answer_outline": evaluation.get("model_answer_outline") or "",
            "feedback": evaluation.get("feedback") or "",
            "citations": citations,
        }

    async def stream_submit(self, session: InterviewSession) -> AsyncGenerator[dict[str, Any], None]:
        if session.phase != "review":
            yield {"type": "error", "message": "Complete all questions and enter review before submitting."}
            return
        if not session.all_answered():
            yield {"type": "error", "message": "Every question must have an answer before submission."}
            return

        yield {"type": "evaluating", "message": "Evaluating your answers against Experience League documentation…", "total": session.total}

        per_question: list[dict[str, Any]] = []
        all_citations: list[dict[str, Any]] = []
        seen_urls: set[str] = set()
        total = session.total

        for i, q in enumerate(session.questions):
            yield {
                "type": "evaluation_progress",
                "question_index": i + 1,
                "total": total,
                "status": "evaluating",
            }
            answer = session.draft_answers.get(q.id, "")
            docs = await self._retrieve_for_question(q, session)
            result = await self._evaluate_single(session, q, answer, docs)
            per_question.append(result)
            yield {
                "type": "question_evaluation",
                "question_id": result["question_id"],
                "question_index": result["question_index"],
                "score": result["score"],
                "score_pct": result["score_pct"],
                "strengths": result["strengths"],
                "gaps": result["gaps"],
                "model_answer_outline": result["model_answer_outline"],
                "citations": result["citations"],
            }
            yield {
                "type": "evaluation_progress",
                "question_index": i + 1,
                "total": total,
                "status": "done",
                "score": result["score"],
            }
            for c in result["citations"]:
                if c["url"] not in seen_urls:
                    seen_urls.add(c["url"])
                    all_citations.append(c)

        session.per_question_results = per_question

        yield {"type": "evaluation_progress", "step": "synthesis"}

        avg_score = round(sum(r["score"] for r in per_question) / len(per_question), 1)
        if self._client:
            try:
                system = build_interviewer_system_prompt(session.level, session.profile_id)  # type: ignore[arg-type]
                synth_prompt = build_session_evaluation_prompt(
                    level=session.level,
                    profile_id=session.profile_id,
                    per_question_results=per_question,
                )
                resp = await self._client.messages.create(
                    model=_MODEL,
                    max_tokens=2000,
                    system=system,
                    messages=[{"role": "user", "content": synth_prompt}],
                )
                raw = resp.content[0].text if resp.content else "{}"
                report = _parse_session_report_json(raw)
            except Exception as exc:
                logger.error("Interviewer session synthesis failed: %s", exc)
                report = {}
        else:
            report = {}

        session_report = {
            "overall_score": float(report.get("overall_score", avg_score)),
            "readiness": report.get("readiness", "needs_work"),
            "readiness_summary": report.get(
                "readiness_summary",
                f"Average score {avg_score}/5 across {len(per_question)} questions.",
            ),
            "strengths": report.get("strengths") or [],
            "priority_gaps": report.get("priority_gaps") or [],
            "mistakes_to_avoid": report.get("mistakes_to_avoid") or [],
            "topics_to_read": report.get("topics_to_read") or [],
            "overall_feedback": report.get("overall_feedback") or "",
            "per_question": per_question,
            "citations": all_citations[:8],
        }
        session.session_report = session_report
        session.phase = "complete"
        session.evaluated = True

        yield {"type": "session_report", **session_report}

        header = (
            f"**Interview debrief — {session_report['overall_score']}/5 overall**\n\n"
            f"**Readiness:** {session_report['readiness_summary']}\n\n"
        )
        feedback = session_report.get("overall_feedback") or ""
        for chunk in _chunk_text(header + feedback):
            yield {"type": "token", "content": chunk}

        yield {
            "type": "session_complete",
            "message": "Evaluation complete. Review your debrief below.",
            "total_answered": len(per_question),
        }
        yield {
            "type": "done",
            "model": "interviewer",
            "session_id": session.session_id,
            **session.to_dict(),
        }


def _chunk_text(text: str, size: int = 48) -> list[str]:
    if not text:
        return []
    return [text[i : i + size] for i in range(0, len(text), size)]
