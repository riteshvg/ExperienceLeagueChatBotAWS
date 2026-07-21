"""
Interviewer Mode pipeline — session management, question delivery, deferred evaluation.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Literal

from backend.core.llm_exceptions import ContentFilterError, RateLimitError
from backend.core.llm_factory import get_messages_client
from backend.core.chroma_retriever import ChromaRetriever
from backend.core.interviewer_prompt import (
    build_evaluation_user_prompt,
    build_followup_detection_prompt,
    build_followup_generation_prompt,
    build_interviewer_system_prompt,
    build_scenario_evaluation_user_prompt,
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
_FOLLOWUP_MODEL = "claude-haiku-4-5-20251001"
SessionPhase = Literal["questioning", "review", "complete"]

# Global per-level strictness applied to scenario questions' deterministic
# score_pct. Not per-question — the rubric pilot didn't calibrate per-question
# per-level thresholds, and inventing per-question numbers without real
# grading data would be guesswork. Senior gets a lenient boost (naming the
# right mechanism matters more than full remediation depth); principal is
# held closer to full rubric coverage for the same score. Revisit once real
# scenario-grading data exists.
LEVEL_SCENARIO_MULTIPLIER = {"senior": 1.15, "architect": 1.0, "principal": 0.90}


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
    created_at: str | None = None

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

    def save_current_answer(self, answer: str, is_voice_input: bool = False) -> dict[str, Any]:
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
        from backend.core import google_db

        google_db.save_interview_answer(self.session_id, q.id, text, True, is_voice_input)
        is_last = self.current_index >= self.total - 1
        return {
            "question_id": q.id,
            "question_index": self.current_index + 1,
            "total_questions": self.total,
            "is_last": is_last,
            "answer": text,
        }

    def update_answer(self, question_id: str, answer: str, is_voice_input: bool = False) -> dict[str, Any]:
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
        from backend.core import google_db

        google_db.update_interview_answer_text(self.session_id, question_id, text, is_voice_input)
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
        is_last = self.current_index >= self.total - 1
        new_index = self.current_index if is_last else self.current_index + 1
        new_phase: SessionPhase = "review" if is_last else "questioning"
        from backend.core import google_db

        if not google_db.try_advance_interview_session(self.session_id, new_index, new_phase):
            # Lost a concurrent /advance race — the other request already applied
            # this exact transition, so from this request's point of view the
            # precondition (awaiting an answer to advance past) no longer holds.
            raise ValueError("Save an answer before moving to the next question.")
        self.awaiting_advance = False
        self.current_index = new_index
        self.phase = new_phase
        if is_last:
            return {"phase": "review", "review_ready": True}
        q = self.current_question()
        return {
            "phase": "questioning",
            "current_index": self.current_index,
            "current_question": _question_to_dict(q, self.current_index, self.total) if q else None,
        }

    def end_interview(self) -> dict[str, Any]:
        """Candidate-initiated early stop: jump straight from 'questioning' to
        'review' regardless of how many questions have been answered, so /submit
        can grade whatever's there. Requires at least one answered question —
        there's nothing to grade otherwise."""
        if self.phase == "complete":
            raise ValueError("Session already completed.")
        if self.phase == "review":
            raise ValueError("Already in review — submit for evaluation when ready.")
        if not any(self.draft_answers.get(q.id, "").strip() for q in self.questions):
            raise ValueError("Answer at least one question before ending the interview.")

        from backend.core import google_db

        if not google_db.try_end_interview_session(self.session_id):
            raise ValueError("Unable to end the interview — session state changed. Please retry.")
        self.phase = "review"
        self.awaiting_advance = False
        return {"phase": "review", "review_ready": True, "ended_early": True}

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

    def insert_followup(self, followup: InterviewQuestion) -> None:
        """Splice a generated follow-up into the in-memory question list right
        after the current question, mirroring the DB-side index shift. self.total
        (len(self.questions)) picks this up immediately since it's a property —
        no separate counter to keep in sync."""
        self.questions.insert(self.current_index + 1, followup)

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
            "created_at": self.created_at,
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
        "is_followup": q.is_followup,
    }


def _question_event(q: InterviewQuestion, index: int, total: int) -> dict[str, Any]:
    return {"type": "question", "question": _question_to_dict(q, index, total)}


def create_session(user_id: str, level: str, profile_id: str) -> InterviewSession:
    questions = get_question_set(level, profile_id, user_id)
    session_id = str(uuid.uuid4())
    from backend.core import google_db

    created_at = google_db.create_interview_session(
        session_id, user_id, level, profile_id,
        [(q.id, q.version) for q in questions],
    )
    return InterviewSession(
        session_id=session_id,
        user_id=user_id,
        level=level,
        profile_id=profile_id,
        questions=questions,
        created_at=created_at,
    )


def get_session(session_id: str) -> InterviewSession | None:
    """Rebuilds a session entirely from Postgres — no in-process cache, so this
    survives a backend restart as long as the session_id is known."""
    from backend.core import google_db

    row = google_db.get_interview_session_row(session_id)
    if row is None:
        return None
    answer_rows = google_db.get_interview_session_answers(session_id)

    questions = [
        InterviewQuestion(
            id=r["question_id"],
            question=r["prompt_text"],
            topic=r["topic"],
            difficulty=r["difficulty"],
            expected_themes=tuple(r["expected_themes"]),
            retrieval_hint=r["retrieval_hint"],
            version=r["question_version"],
            is_followup=r["is_followup"],
        )
        for r in answer_rows
    ]
    draft_answers = {r["question_id"]: r["answer"] for r in answer_rows if r["answer"]}

    per_question_results: list[dict[str, Any]] = []
    for i, r in enumerate(answer_rows):
        if r["score"] is None:
            continue
        per_question_results.append({
            "question_id": r["question_id"],
            "question_index": i + 1,
            "question": r["prompt_text"],
            "topic": r["topic"],
            "answer": r["answer"],
            "score": r["score"],
            "score_pct": r["score_pct"],
            "strengths": r["strengths"] or [],
            "gaps": r["gaps"] or [],
            "model_answer_outline": r["model_answer_outline"] or "",
            "feedback": r["feedback"] or "",
            "citations": r["citations"] or [],
        })

    return InterviewSession(
        session_id=row["session_id"],
        user_id=row["user_id"],
        level=row["level"],
        profile_id=row["profile_id"],
        questions=questions,
        current_index=row["current_index"],
        phase=row["phase"],
        awaiting_advance=row["awaiting_advance"],
        draft_answers=draft_answers,
        evaluated=row["evaluated"],
        per_question_results=per_question_results,
        session_report=row["session_report"],
        created_at=row["created_at"],
    )


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


def _docs_to_citations(docs: list[dict], min_score: float = 0.0) -> list[dict[str, Any]]:
    """`min_score` guards against retrieve_with_refinement's neighbor-probe fallback,
    which can legitimately ignore the product where_filter and return a cross-product
    doc when the filtered search comes back too weak — an acceptable tradeoff for the
    main chat UX ("something beats nothing"), but not for a "Suggested reading" list
    where a confidently-wrong link (e.g. a CJA question citing a Marketo Engage doc)
    is worse than citing nothing at all."""
    citations: list[dict[str, Any]] = []
    seen: set[str] = set()
    for doc in docs[:5]:
        score = doc.get("score")
        if score is not None and score < min_score:
            continue
        meta = doc.get("metadata") or {}
        url = meta.get("url") or meta.get("source_url") or ""
        if not url or url in seen:
            continue
        seen.add(url)
        citations.append({
            "url": url,
            "title": meta.get("title") or url,
            "product": meta.get("product"),
            "score": score,
        })
    return citations


def _extract_json_object(text: str) -> dict[str, Any] | None:
    """Best-effort extraction of a JSON object from an LLM response, tolerant of
    a response that got cut off by max_tokens before the closing fence/brace
    ever arrived. Strips a ```json fence (with or without its closing ```),
    then scans from the first '{' tracking bracket/string state so a
    truncated-mid-object response can be repaired by closing whatever was
    still open, rather than failing to parse entirely."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"```\s*$", "", text).strip()

    start = text.find("{")
    if start == -1:
        return None
    text = text[start:]

    stack: list[str] = []
    in_string = False
    escape = False
    close_index: int | None = None
    for i, ch in enumerate(text):
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch in "{[":
            stack.append(ch)
        elif ch in "}]":
            if stack:
                stack.pop()
            if not stack:
                close_index = i
                break

    if close_index is not None:
        candidate = text[: close_index + 1]
    else:
        # Truncated mid-object — repair by closing whatever was left open.
        candidate = text
        if in_string:
            candidate += '"'
        candidate = candidate.rstrip()
        candidate = re.sub(r",\s*$", "", candidate)
        for opener in reversed(stack):
            candidate += "}" if opener == "{" else "]"

    try:
        data = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _parse_evaluation_json(text: str) -> dict[str, Any]:
    data = _extract_json_object(text)
    if data is not None:
        return data
    return {
        "score": 3,
        "score_pct": 60,
        "strengths": [],
        "gaps": ["Could not parse structured evaluation."],
        "model_answer_outline": "",
        "feedback": text.strip(),
    }


def _parse_scenario_evaluation_json(text: str) -> dict[str, Any]:
    data = _extract_json_object(text)
    if data is not None and isinstance(data.get("matched_points"), list):
        return data
    return {"matched_points": [], "feedback": text.strip()}


def _score_from_rubric_match(
    grading_rubric: dict, matched_points: list[dict], level: str,
) -> dict[str, Any]:
    """Deterministic scoring for scenario questions: score_pct is the weighted
    fraction of rubric points the model judged as matched, then adjusted by a
    global per-level strictness multiplier and banded into the same 1-5 scale
    standard questions use, so the two question types stay comparable."""
    rubric_points = grading_rubric.get("required_points") or grading_rubric.get("partial_credit_points") or []
    weights_by_point = {p["point"]: p["weight"] for p in rubric_points}
    total_weight = sum(weights_by_point.values()) or 1.0

    matched_by_point = {m.get("point"): bool(m.get("matched")) for m in matched_points}
    matched_weight = sum(
        weight for point, weight in weights_by_point.items() if matched_by_point.get(point)
    )

    raw_pct = 100 * matched_weight / total_weight
    multiplier = LEVEL_SCENARIO_MULTIPLIER.get(level, 1.0)
    score_pct = max(0, min(100, round(raw_pct * multiplier)))

    if score_pct >= 90:
        score = 5
    elif score_pct >= 75:
        score = 4
    elif score_pct >= 60:
        score = 3
    elif score_pct >= 40:
        score = 2
    else:
        score = 1

    strengths = [point for point in weights_by_point if matched_by_point.get(point)]
    gaps = sorted(
        (point for point in weights_by_point if not matched_by_point.get(point)),
        key=lambda p: weights_by_point[p],
        reverse=True,
    )
    model_answer_outline = " · ".join(weights_by_point.keys())

    return {
        "score": score,
        "score_pct": score_pct,
        "strengths": strengths,
        "gaps": gaps,
        "model_answer_outline": model_answer_outline,
    }


def _parse_session_report_json(text: str) -> dict[str, Any]:
    data = _extract_json_object(text)
    if data is not None:
        return data
    return {
        "readiness": "needs_work",
        "readiness_summary": "Review the per-question feedback below.",
        "strengths": [],
        "priority_gaps": [],
        "mistakes_to_avoid": [],
        "topics_to_read": [],
        "overall_feedback": text.strip(),
    }


class InterviewerPipeline:
    def __init__(self, retriever: ChromaRetriever | None):
        self.retriever = retriever
        self._processor = QueryProcessor()
        self._client = get_messages_client(get_settings())

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

    async def _retrieve_for_query(self, search_query: str, session: InterviewSession) -> list[dict]:
        """Shared retrieval helper, scoped to the session's product — used both for
        per-question grading context and for grounding "topics to study" in real
        links. Bug fix: `product` was previously only passed to
        retrieve_with_refinement's `product_filter` arg, which only informs its
        refinement heuristics — the actual ChromaDB query never had a `where`
        constraint, so retrieval silently searched the entire KB across all
        products. Build the same where_filter the main chat pipeline uses
        (rag_pipeline.py) so a CJA question can't surface an unrelated product's
        doc (e.g. Marketo Engage) as a citation."""
        if not self.retriever:
            return []
        product = _product_filter(session.profile_id) or detect_product_intent(search_query)
        where_filter = {"product": {"$eq": product}} if product else None
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
                where_filter=where_filter,
            )
            return docs
        except Exception as exc:
            logger.warning("Interviewer retrieval failed: %s", exc)
            return []

    async def _retrieve_for_question(self, q: InterviewQuestion, session: InterviewSession) -> list[dict]:
        return await self._retrieve_for_query(f"{q.retrieval_hint} {q.topic}", session)

    @staticmethod
    def _citation_from_contributing_questions(
        source_question_indices: list[Any], per_question: list[dict[str, Any]]
    ) -> dict[str, str] | None:
        """Ground a "topics to study" link in the citations that actually backed the
        grading of the question(s) this topic was synthesized from, instead of
        re-retrieving from the topic label alone (which drifts to unrelated docs —
        e.g. a short label like "CJA Architecture" can vector-match a Marketo page).
        Selection rule: union the citations of every contributing question, dedupe by
        URL, keep the highest retrieval score seen for each — the top-scored citation
        wins as the primary link."""
        indices = {int(i) for i in source_question_indices if isinstance(i, (int, float, str)) and str(i).strip()}
        if not indices:
            return None
        best_by_url: dict[str, dict[str, Any]] = {}
        for row in per_question:
            if row.get("question_index") not in indices:
                continue
            for c in row.get("citations") or []:
                url = c.get("url")
                if not url:
                    continue
                score = c.get("score") or 0
                existing = best_by_url.get(url)
                if existing is None or score > (existing.get("score") or 0):
                    best_by_url[url] = c
        if not best_by_url:
            return None
        top = max(best_by_url.values(), key=lambda c: c.get("score") or 0)
        return {"url": top["url"], "title": top.get("title") or top["url"]}

    async def _ground_topic_link(self, topic: str, session: InterviewSession) -> dict[str, str] | None:
        """Fallback only: used when the synthesis step didn't tag a topic with
        source_question_indices (or those questions had no citations), so there's
        nothing to ground against — fresh scoped retrieval on the topic label is a
        last resort, not the primary path."""
        docs = await self._retrieve_for_query(topic, session)
        settings = get_settings()
        for doc in docs:
            score = doc.get("score")
            if score is not None and score < settings.similarity_threshold:
                continue
            meta = doc.get("metadata") or {}
            url = meta.get("url") or meta.get("source_url") or ""
            if url:
                return {"url": url, "title": meta.get("title") or url}
        return None

    async def maybe_generate_followup(
        self, session: InterviewSession, q: InterviewQuestion, answer: str
    ) -> dict[str, Any] | None:
        """Cheap Haiku check on a just-saved answer: thin or off-target for the
        candidate's level? If so, generate one targeted follow-up from the same
        retrieval scope used for grading and persist it immediately after `q`.
        Fails open on any error — this must never block /answer from returning.
        Returns a dict describing the follow-up (for the /answer response and for
        splicing into session.questions), or None if no follow-up was generated.
        """
        if q.is_followup:
            # No chaining: a follow-up's own answer never spawns another follow-up,
            # no matter how weak it is. This is the sole authoritative guard for the
            # "one follow-up per weak answer" cap — get_followup_for_parent below
            # only checks whether q already HAS a follow-up, not whether q itself
            # IS one, so without this early return a weak answer to a follow-up
            # would produce a second, chained follow-up.
            return None

        from backend.core import google_db

        existing = google_db.get_followup_for_parent(session.session_id, q.id)
        if existing is not None:
            return self._followup_dict(q, existing)

        if not self._client:
            return None  # no ANTHROPIC_API_KEY configured — feature silently unavailable

        try:
            docs = await self._retrieve_for_question(q, session)
            doc_context = _build_doc_context(docs)

            detection_prompt = build_followup_detection_prompt(
                question=q.question, topic=q.topic, level=session.level,
                candidate_answer=answer, doc_context=doc_context,
            )
            detect_resp = await asyncio.wait_for(
                self._client.messages.create(
                    model=_FOLLOWUP_MODEL, max_tokens=10,
                    messages=[{"role": "user", "content": detection_prompt}],
                ),
                timeout=5.0,
            )
            verdict = (detect_resp.content[0].text if detect_resp.content else "").strip().upper()
            if not verdict.startswith("WEAK"):
                return None

            gen_prompt = build_followup_generation_prompt(
                question=q.question, topic=q.topic, level=session.level,
                candidate_answer=answer, doc_context=doc_context,
            )
            gen_resp = await asyncio.wait_for(
                self._client.messages.create(
                    model=_FOLLOWUP_MODEL, max_tokens=200,
                    messages=[{"role": "user", "content": gen_prompt}],
                ),
                timeout=5.0,
            )
            followup_text = (gen_resp.content[0].text if gen_resp.content else "").strip()
            if not followup_text:
                return None
        except Exception as exc:
            logger.warning("Interviewer follow-up detection/generation failed for %s: %s", q.id, exc)
            return None

        persisted = google_db.insert_followup_if_absent(session.session_id, q.id, q.version, followup_text)
        return self._followup_dict(q, persisted)

    @staticmethod
    def _followup_dict(parent: InterviewQuestion, persisted: dict[str, Any]) -> dict[str, Any]:
        return {
            "question_id": persisted["question_id"],
            "question_index": persisted["question_index"] + 1,
            "question": persisted["followup_prompt_text"],
            "topic": parent.topic,
            "difficulty": parent.difficulty,
            "expected_themes": list(parent.expected_themes),
            "parent_question_id": parent.id,
        }

    async def _evaluate_single(
        self,
        session: InterviewSession,
        q: InterviewQuestion,
        answer: str,
        docs: list[dict],
    ) -> dict[str, Any]:
        doc_context = _build_doc_context(docs)
        citations = _docs_to_citations(docs, min_score=get_settings().similarity_threshold)
        is_scenario = q.question_type == "scenario" and q.grading_rubric

        if self._client:
            try:
                system = build_interviewer_system_prompt(session.level, session.profile_id)  # type: ignore[arg-type]
                if is_scenario:
                    user_prompt = build_scenario_evaluation_user_prompt(
                        question=q.question,
                        grading_rubric=q.grading_rubric,
                        level=session.level,
                        candidate_answer=answer,
                        doc_context=doc_context,
                    )
                else:
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
                    max_tokens=2500,
                    system=system,
                    messages=[{"role": "user", "content": user_prompt}],
                )
                raw = resp.content[0].text if resp.content else "{}"
                if is_scenario:
                    scenario_eval = _parse_scenario_evaluation_json(raw)
                    evaluation = _score_from_rubric_match(
                        q.grading_rubric, scenario_eval["matched_points"], session.level,
                    )
                    evaluation["feedback"] = scenario_eval.get("feedback", "")
                else:
                    evaluation = _parse_evaluation_json(raw)
            except RateLimitError as exc:
                logger.warning("Interviewer per-question eval rate-limited: %s", exc)
                evaluation = {
                    "score": 3,
                    "score_pct": 60,
                    "strengths": [],
                    "gaps": ["Evaluation service is busy right now — this answer wasn't scored in detail."],
                    "model_answer_outline": "",
                    "feedback": "",
                }
            except ContentFilterError as exc:
                logger.warning("Interviewer per-question eval content-filtered: %s", exc)
                evaluation = {
                    "score": 3,
                    "score_pct": 60,
                    "strengths": [],
                    "gaps": ["Evaluation response was blocked by content filtering."],
                    "model_answer_outline": "",
                    "feedback": "",
                }
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

    async def stream_submit(
        self, session: InterviewSession, stale_after_seconds: int = 120
    ) -> AsyncGenerator[dict[str, Any], None]:
        if session.phase != "review":
            yield {"type": "error", "message": "Complete all questions and enter review before submitting."}
            return

        # Grade only the questions that actually have an answer. Normally every
        # question is answered by the time /advance reaches "review" — but the
        # candidate-initiated "End interview" path (end_interview()) can land here
        # early with some questions never answered, and those simply aren't graded.
        answered_questions = [q for q in session.questions if session.draft_answers.get(q.id, "").strip()]
        questions_total = session.total
        questions_answered = len(answered_questions)
        if questions_answered == 0:
            yield {"type": "error", "message": "No answered questions to evaluate."}
            return

        from backend.core import google_db

        claim_token = google_db.try_claim_interview_session_for_evaluation(session.session_id, stale_after_seconds)
        if claim_token is None:
            # Lost a concurrent /submit race — another request already claimed this
            # session for evaluation. Don't re-run the (expensive) LLM evaluation.
            yield {"type": "error", "message": "Session already evaluated"}
            return
        session.evaluated = True

        yield {"type": "evaluating", "message": "Evaluating your answers against Experience League documentation…", "total": questions_answered}

        per_question: list[dict[str, Any]] = []
        all_citations: list[dict[str, Any]] = []
        seen_urls: set[str] = set()

        for i, q in enumerate(answered_questions):
            yield {
                "type": "evaluation_progress",
                "question_index": i + 1,
                "total": questions_answered,
                "status": "evaluating",
            }
            answer = session.draft_answers.get(q.id, "").strip()
            docs = await self._retrieve_for_question(q, session)
            result = await self._evaluate_single(session, q, answer, docs)
            per_question.append(result)
            wrote = google_db.record_question_evaluation(
                session.session_id,
                result["question_id"],
                result["score"],
                result["score_pct"],
                result["strengths"],
                result["gaps"],
                result["model_answer_outline"],
                result["feedback"],
                result["citations"],
                claim_token,
            )
            if not wrote:
                # A stale reclaim took this session's evaluation away from us mid-flight
                # (e.g. a duplicate /submit fired after we'd been sitting stalled long
                # enough to look abandoned). Stop burning further LLM calls — whichever
                # run now holds the claim owns finishing this evaluation.
                logger.warning(
                    "Interviewer session %s lost its evaluation claim mid-submit; stopping.",
                    session.session_id,
                )
                yield {"type": "error", "message": "Evaluation was taken over by another request."}
                return
            yield {
                "type": "question_evaluation",
                "question_id": result["question_id"],
                "question_index": i + 1,
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
                "total": questions_answered,
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
                    max_tokens=4096,
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

        topics_to_read: list[dict[str, Any]] = []
        for entry in (report.get("topics_to_read") or [])[:8]:
            topic_text = (entry.get("topic") or "").strip()
            item = {"topic": topic_text, "reason": entry.get("reason") or ""}
            link = self._citation_from_contributing_questions(
                entry.get("source_question_indices") or [], per_question
            )
            if link is None and topic_text:
                link = await self._ground_topic_link(topic_text, session)
            if link:
                item["url"] = link["url"]
                item["title"] = link["title"]
            topics_to_read.append(item)

        default_summary = f"Average score {avg_score}/5 across {questions_answered} questions."
        if questions_answered < questions_total:
            default_summary += f" ({questions_total - questions_answered} question(s) skipped — interview ended early.)"

        session_report = {
            # Deterministic mean of per-question scores — never an independent LLM
            # judgment, which was found to silently diverge from the real numbers
            # (e.g. reporting 4.0/5 while per-question scores averaged 3.7/5).
            "overall_score": avg_score,
            "readiness": report.get("readiness", "needs_work"),
            "readiness_summary": report.get("readiness_summary", default_summary),
            "strengths": report.get("strengths") or [],
            "priority_gaps": report.get("priority_gaps") or [],
            "mistakes_to_avoid": report.get("mistakes_to_avoid") or [],
            "topics_to_read": topics_to_read,
            "overall_feedback": report.get("overall_feedback") or "",
            "per_question": per_question,
            "citations": all_citations[:8],
            "questions_answered": questions_answered,
            "questions_total": questions_total,
        }
        completed = google_db.complete_interview_session(session.session_id, session_report, claim_token)
        if not completed:
            # We finished the (expensive) evaluation work, but a stale reclaim took
            # the claim away from us before we could write the report — some other
            # run now owns (or already wrote) this session's completion. Discard our
            # result rather than overwriting whatever that run persisted.
            logger.warning(
                "Interviewer session %s lost its evaluation claim before completion; discarding report.",
                session.session_id,
            )
            yield {"type": "error", "message": "Evaluation was taken over by another request."}
            return

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
