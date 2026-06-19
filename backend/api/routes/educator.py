"""
Educator Mode API — admin-gated exam prep chat.

POST /api/educator/chat     — SSE stream (educator agent)
GET  /api/educator/exams    — exam registry
GET  /api/educator/status   — feature flag + admin eligibility
POST /api/educator/score    — readiness report JSON
POST /api/educator/log      — append session log (beta analytics)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from backend.api.deps import get_educator_user, get_retriever, get_session_store
from backend.core.educator_pipeline import EducatorPipeline
from backend.core.readiness_report import generate_readiness_report, readiness_report_to_dict
from backend.core.session_store import SessionStore
from config.exams import exams_for_api, get_exam
from config.settings import get_data_dir, get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/educator", tags=["educator"])

_EDUCATOR_LOG = get_data_dir() / "educator_sessions.jsonl"


class ChatMessage(BaseModel):
    role: str
    content: str


class EducatorChatRequest(BaseModel):
    messages: list[ChatMessage]
    exam_id: str
    session_id: Optional[str] = None
    domain_scores: dict[str, dict[str, int]] = Field(default_factory=dict)
    question_number: int = 1


class ScoreRequest(BaseModel):
    exam_id: str
    domain_scores: dict[str, dict[str, int]] = Field(default_factory=dict)
    total_correct: Optional[int] = None
    total_asked: Optional[int] = None


class SessionLogRequest(BaseModel):
    exam_id: str
    domain_scores: dict[str, dict[str, int]] = Field(default_factory=dict)
    questions_asked: int = 0
    session_started: Optional[int] = None
    duration_secs: Optional[int] = None


@router.get("/status")
async def educator_status(user: Annotated[dict, Depends(get_educator_user)]):
    settings = get_settings()
    return {
        "enabled": settings.educator_mode_enabled,
        "is_admin": user.get("is_admin", False),
        "email": user.get("email", ""),
    }


@router.get("/exams")
async def list_exams(_: Annotated[dict, Depends(get_educator_user)]):
    return {"exams": exams_for_api()}


@router.post("/score")
async def score_report(body: ScoreRequest, _: Annotated[dict, Depends(get_educator_user)]):
    exam = get_exam(body.exam_id)
    if not exam:
        raise HTTPException(status_code=400, detail="Unknown exam ID")
    report = generate_readiness_report(
        exam,
        body.domain_scores,
        body.total_correct,
        body.total_asked,
    )
    return readiness_report_to_dict(report)


@router.post("/log")
async def log_session(
    body: SessionLogRequest,
    user: Annotated[dict, Depends(get_educator_user)],
):
    entry = {
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "email": user.get("email", ""),
        "user_id": user.get("uid", ""),
        "exam_id": body.exam_id,
        "questions_asked": body.questions_asked,
        "domain_scores": body.domain_scores,
        "session_started": body.session_started,
        "duration_secs": body.duration_secs,
    }
    try:
        _EDUCATOR_LOG.parent.mkdir(parents=True, exist_ok=True)
        with _EDUCATOR_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as exc:
        logger.warning(f"Educator session log failed: {exc}")
    return {"logged": True}


@router.post("/chat")
async def educator_chat(
    body: EducatorChatRequest,
    request: Request,
    user: Annotated[dict, Depends(get_educator_user)],
    session_store: Annotated[SessionStore, Depends(get_session_store)],
):
    retriever = get_retriever(request)
    if retriever is None:
        raise HTTPException(status_code=503, detail="Knowledge base unavailable")

    exam = get_exam(body.exam_id)
    if not exam:
        raise HTTPException(status_code=400, detail="Unknown exam ID")

    session_id = body.session_id or session_store.new_session()
    pipeline = EducatorPipeline(retriever=retriever, session_store=session_store)
    messages = [{"role": m.role, "content": m.content} for m in body.messages]

    async def event_generator():
        async for event in pipeline.stream(
            messages=messages,
            exam_id=body.exam_id,
            domain_scores=body.domain_scores,
            session_id=session_id,
            question_number=body.question_number,
        ):
            yield {"data": json.dumps(event)}

    return EventSourceResponse(event_generator())


@router.post("/reset")
async def reset_educator(_: Annotated[dict, Depends(get_educator_user)]):
    return {"reset": True, "mode": "standard"}
