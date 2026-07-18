"""
Interviewer Mode API — mock interview prep with deferred KB-grounded evaluation.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from backend.api.deps import get_retriever, get_site_user
from backend.core import google_db
from backend.core.chroma_retriever import ChromaRetriever
from backend.core.interviewer_pipeline import (
    InterviewerPipeline,
    create_session,
    get_session,
)
from backend.core.voice_transcription import TranscriptionError, transcribe_audio
from config.interview_profiles import get_profiles_payload, validate_profile
from config.settings import get_settings

_MAX_AUDIO_BYTES = 6 * 1024 * 1024  # ~4 min of webm/opus at typical mic bitrate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/interviewer", tags=["interviewer"])


def _settings():
    return get_settings()


def _user_is_admin(user: dict) -> bool:
    admin_email = os.getenv("ADMIN_EMAIL", "").strip().lower()
    if admin_email and user.get("email", "").strip().lower() == admin_email:
        return True
    try:
        from backend.core import google_db

        for row in google_db.list_users():
            if row.get("user_id") == user.get("uid"):
                return bool(row.get("is_admin"))
    except Exception as exc:
        logger.debug("Admin check fallback: %s", exc)
    return False


def _user_in_interviewer_allowlist(user: dict) -> bool:
    """Staged-access cohort for Phase 2: a small named group can use Interviewer
    Mode ahead of general availability without flipping INTERVIEWER_MODE_ADMIN_ONLY
    off entirely. Comma-separated Google `sub` (uid) or email values — edit the
    env var and restart to add/remove someone, no deploy or migration needed."""
    allowlist = os.getenv("INTERVIEWER_MODE_ALLOWLIST", "")
    if not allowlist.strip():
        return False
    allowed = {entry.strip().lower() for entry in allowlist.split(",") if entry.strip()}
    uid = (user.get("uid") or "").strip().lower()
    email = (user.get("email") or "").strip().lower()
    return uid in allowed or email in allowed


def _feature_available(user: dict) -> bool:
    s = _settings()
    if not s.interviewer_mode_enabled:
        return False
    if s.interviewer_mode_admin_only and not _user_is_admin(user) and not _user_in_interviewer_allowlist(user):
        return False
    return True


def _require_feature(user: dict) -> None:
    if not _feature_available(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="INTERVIEWER_MODE_UNAVAILABLE",
        )


def _get_owned_session(session_id: str, user: dict):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")
    if session.user_id != (user.get("uid") or user.get("email", "")):
        raise HTTPException(status_code=403, detail="Session access denied")
    return session


class StartRequest(BaseModel):
    level: str
    profile_id: str = Field(..., description="Solution id or principal collection id")


class SessionRequest(BaseModel):
    session_id: str


class AnswerRequest(BaseModel):
    session_id: str
    answer: str
    is_voice_input: bool = False


class EditAnswerRequest(BaseModel):
    session_id: str
    question_id: str
    answer: str
    is_voice_input: bool = False


class InterviewFeedbackRequest(BaseModel):
    session_id: str
    status: str = Field("submitted", description="'submitted' or 'dismissed'")
    questions_match_level: Optional[int] = None
    feedback_quality: Optional[int] = None
    suggestions: Optional[str] = None
    would_recommend: Optional[bool] = None


@router.get("/status")
async def interviewer_status(user: Annotated[dict, Depends(get_site_user)]):
    s = _settings()
    return {
        "enabled": s.interviewer_mode_enabled,
        "admin_only": s.interviewer_mode_admin_only,
        "available": _feature_available(user),
        "is_admin": _user_is_admin(user),
    }


@router.get("/profiles")
async def interviewer_profiles(user: Annotated[dict, Depends(get_site_user)]):
    _require_feature(user)
    return get_profiles_payload()


@router.post("/start")
async def start_interview(
    body: StartRequest,
    request: Request,
    retriever: Annotated[Optional[ChromaRetriever], Depends(get_retriever)],
    user: Annotated[dict, Depends(get_site_user)],
):
    _require_feature(user)
    err = validate_profile(body.level, body.profile_id)
    if err:
        raise HTTPException(status_code=400, detail=err)

    session = create_session(
        user_id=user.get("uid") or user.get("email", ""),
        level=body.level,
        profile_id=body.profile_id,
    )
    pipeline = InterviewerPipeline(retriever)

    async def event_generator():
        async for event in pipeline.stream_start(session):
            yield {"data": json.dumps(event)}

    return EventSourceResponse(event_generator())


@router.post("/answer")
async def save_answer(
    body: AnswerRequest,
    retriever: Annotated[Optional[ChromaRetriever], Depends(get_retriever)],
    user: Annotated[dict, Depends(get_site_user)],
):
    _require_feature(user)
    session = _get_owned_session(body.session_id, user)
    if session.completed:
        raise HTTPException(status_code=400, detail="Interview session already completed")
    parent_question = session.current_question()
    try:
        result = session.save_current_answer(body.answer, is_voice_input=body.is_voice_input)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if parent_question is not None and not body.is_voice_input:
        pipeline = InterviewerPipeline(retriever)
        follow_up = await pipeline.maybe_generate_followup(session, parent_question, body.answer)
        if follow_up is not None:
            from config.interview_profiles import InterviewQuestion

            session.insert_followup(InterviewQuestion(
                id=follow_up["question_id"],
                question=follow_up["question"],
                topic=follow_up["topic"],
                difficulty=follow_up["difficulty"],
                expected_themes=tuple(follow_up["expected_themes"]),
                retrieval_hint=parent_question.retrieval_hint,
                version=parent_question.version,
                is_followup=True,
            ))
            result["total_questions"] = session.total
            result["is_last"] = False
            result["follow_up"] = follow_up

    return {**result, **session.to_dict()}


@router.post("/transcribe")
async def transcribe_answer(
    session_id: Annotated[str, Form(...)],
    audio: Annotated[UploadFile, File(...)],
    user: Annotated[dict, Depends(get_site_user)],
):
    _require_feature(user)
    _get_owned_session(session_id, user)

    user_id = user.get("uid") or user.get("email", "")
    if not google_db.check_transcription_rate_limit(user_id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many transcription requests — please slow down and try again shortly.",
        )

    audio_bytes = await audio.read()
    if len(audio_bytes) > _MAX_AUDIO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recording too long — please keep answers under about 4 minutes.",
        )
    if not audio_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No audio received.")

    try:
        transcript = await transcribe_audio(audio_bytes, filename=audio.filename or "answer.webm")
    except TranscriptionError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return {"transcript": transcript}


@router.patch("/answer")
async def edit_answer(
    body: EditAnswerRequest,
    user: Annotated[dict, Depends(get_site_user)],
):
    _require_feature(user)
    session = _get_owned_session(body.session_id, user)
    if session.completed:
        raise HTTPException(status_code=400, detail="Interview session already completed")
    try:
        result = session.update_answer(body.question_id, body.answer, is_voice_input=body.is_voice_input)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {**result, **session.to_dict()}


@router.post("/advance")
async def advance_question(
    body: SessionRequest,
    user: Annotated[dict, Depends(get_site_user)],
):
    _require_feature(user)
    session = _get_owned_session(body.session_id, user)
    if session.completed:
        raise HTTPException(status_code=400, detail="Interview session already completed")
    try:
        result = session.advance()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    payload = {**result, **session.to_dict()}
    if result.get("current_question"):
        payload["current_question"] = result["current_question"]
    return payload


@router.post("/end")
async def end_interview(
    body: SessionRequest,
    user: Annotated[dict, Depends(get_site_user)],
):
    """Candidate-initiated early stop: jump straight to review with whatever's
    been answered so far, so it can be graded via the normal /submit flow."""
    _require_feature(user)
    session = _get_owned_session(body.session_id, user)
    if session.completed:
        raise HTTPException(status_code=400, detail="Interview session already completed")
    try:
        result = session.end_interview()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {**result, **session.to_dict()}


@router.get("/review/{session_id}")
async def get_review(
    session_id: str,
    user: Annotated[dict, Depends(get_site_user)],
):
    _require_feature(user)
    session = _get_owned_session(session_id, user)
    feedback = google_db.get_interview_feedback(session_id)
    return {
        "items": session.get_review_items(),
        "all_answered": session.all_answered(),
        "feedback_status": feedback["status"] if feedback else None,
        **session.to_dict(),
    }


@router.post("/feedback")
async def submit_interview_feedback(
    body: InterviewFeedbackRequest,
    user: Annotated[dict, Depends(get_site_user)],
):
    """Beta-tester feedback for a completed interview's debrief. Covers both
    an actual submission and a dismiss (status='dismissed', all ratings
    None) — the dismiss case exists so the form doesn't reappear if the
    candidate revisits this session's debrief later. No LLM call involved."""
    _require_feature(user)
    if body.status not in ("submitted", "dismissed"):
        raise HTTPException(status_code=400, detail="status must be 'submitted' or 'dismissed'")
    session = _get_owned_session(body.session_id, user)
    google_db.save_interview_feedback(
        session.session_id,
        session.user_id,
        status=body.status,
        questions_match_level=body.questions_match_level,
        feedback_quality=body.feedback_quality,
        suggestions=body.suggestions,
        would_recommend=body.would_recommend,
    )
    return {"status": "ok"}


@router.post("/submit")
async def submit_for_evaluation(
    body: SessionRequest,
    retriever: Annotated[Optional[ChromaRetriever], Depends(get_retriever)],
    user: Annotated[dict, Depends(get_site_user)],
):
    _require_feature(user)
    session = _get_owned_session(body.session_id, user)
    if session.phase == "complete":
        raise HTTPException(status_code=400, detail="Session already evaluated")

    pipeline = InterviewerPipeline(retriever)

    async def event_generator():
        async for event in pipeline.stream_submit(session):
            yield {"data": json.dumps(event)}

    return EventSourceResponse(event_generator())
