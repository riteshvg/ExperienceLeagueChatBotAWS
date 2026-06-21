"""
Interviewer Mode API — mock interview prep with deferred KB-grounded evaluation.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from backend.api.deps import get_retriever, get_site_user
from backend.core.chroma_retriever import ChromaRetriever
from backend.core.interviewer_pipeline import (
    InterviewerPipeline,
    create_session,
    get_session,
)
from config.interview_profiles import get_profiles_payload, validate_profile
from config.settings import get_settings

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


def _feature_available(user: dict) -> bool:
    s = _settings()
    if not s.interviewer_mode_enabled:
        return False
    if s.interviewer_mode_admin_only and not _user_is_admin(user):
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


class EditAnswerRequest(BaseModel):
    session_id: str
    question_id: str
    answer: str


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
    user: Annotated[dict, Depends(get_site_user)],
):
    _require_feature(user)
    session = _get_owned_session(body.session_id, user)
    if session.completed:
        raise HTTPException(status_code=400, detail="Interview session already completed")
    try:
        result = session.save_current_answer(body.answer)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {**result, **session.to_dict()}


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
        result = session.update_answer(body.question_id, body.answer)
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


@router.get("/review/{session_id}")
async def get_review(
    session_id: str,
    user: Annotated[dict, Depends(get_site_user)],
):
    _require_feature(user)
    session = _get_owned_session(session_id, user)
    return {
        "items": session.get_review_items(),
        "all_answered": session.all_answered(),
        **session.to_dict(),
    }


@router.post("/submit")
async def submit_for_evaluation(
    body: SessionRequest,
    retriever: Annotated[Optional[ChromaRetriever], Depends(get_retriever)],
    user: Annotated[dict, Depends(get_site_user)],
):
    _require_feature(user)
    session = _get_owned_session(body.session_id, user)
    if session.evaluated:
        raise HTTPException(status_code=400, detail="Session already evaluated")

    pipeline = InterviewerPipeline(retriever)

    async def event_generator():
        async for event in pipeline.stream_submit(session):
            yield {"data": json.dumps(event)}

    return EventSourceResponse(event_generator())
