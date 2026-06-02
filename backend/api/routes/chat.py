"""
Chat endpoint — POST /api/chat

Streams tokens + citations back to the client using Server-Sent Events.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Optional

from anthropic import AsyncAnthropic
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from backend.api.deps import get_pipeline, get_session_store, get_site_user
from backend.core.rag_pipeline import RAGPipeline
from backend.core.session_store import SessionStore

_ROOT = Path(__file__).parent.parent.parent.parent
FEEDBACK_FILE = _ROOT / "data" / "feedback.jsonl"

logger = logging.getLogger(__name__)
router = APIRouter()


class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    haiku_only: bool = False


@router.post("/chat")
async def chat(
    body: ChatRequest,
    pipeline: Annotated[RAGPipeline, Depends(get_pipeline)],
    session_store: Annotated[SessionStore, Depends(get_session_store)],
    _user: Annotated[str, Depends(get_site_user)],
):
    # Create a new session if none provided
    session_id = body.session_id or session_store.new_session()

    async def event_generator():
        async for event in pipeline.stream(
            query=body.query,
            session_id=session_id,
            haiku_only=body.haiku_only,
        ):
            yield {"data": json.dumps(event)}

    return EventSourceResponse(event_generator())


@router.get("/chat/history/{session_id}")
async def get_history(
    session_id: str,
    session_store: Annotated[SessionStore, Depends(get_session_store)],
):
    return {"session_id": session_id, "history": session_store.get_history(session_id)}


@router.delete("/chat/history/{session_id}")
async def clear_history(
    session_id: str,
    session_store: Annotated[SessionStore, Depends(get_session_store)],
):
    session_store.clear(session_id)
    return {"session_id": session_id, "cleared": True}


@router.post("/chat/session")
async def new_session(
    session_store: Annotated[SessionStore, Depends(get_session_store)],
):
    """Create a fresh session and return its ID."""
    return {"session_id": session_store.new_session()}


class FollowUpsRequest(BaseModel):
    query: str
    answer: str


@router.post("/chat/follow-ups")
async def get_follow_ups(body: FollowUpsRequest, _user: Annotated[str, Depends(get_site_user)]):
    """Generate 3 follow-up questions using Haiku."""
    import os
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return {"follow_ups": []}

    client = AsyncAnthropic(api_key=api_key)
    prompt = (
        f"Based on this question and answer, suggest exactly 3 concise follow-up questions "
        f"a user might ask next. Return only the 3 questions as a JSON array of strings, "
        f"nothing else.\n\nQuestion: {body.query}\n\nAnswer summary: {body.answer[:500]}"
    )
    try:
        resp = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip()
        # Parse JSON array
        import re
        match = re.search(r'\[.*?\]', raw, re.DOTALL)
        follow_ups = json.loads(match.group()) if match else []
        return {"follow_ups": follow_ups[:3]}
    except Exception as e:
        logger.warning(f"Follow-ups generation failed: {e}")
        return {"follow_ups": []}


class FeedbackRequest(BaseModel):
    message_id: str
    session_id: str
    rating: int  # 1 or -1
    query: str


@router.post("/chat/feedback")
async def submit_feedback(body: FeedbackRequest, _user: Annotated[str, Depends(get_site_user)]):
    """Store user feedback to data/feedback.jsonl."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message_id": body.message_id,
        "session_id": body.session_id,
        "rating": body.rating,
        "query": body.query,
    }
    FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(FEEDBACK_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return {"status": "ok"}
