"""
Chat endpoint — POST /api/chat

Streams tokens + citations back to the client using Server-Sent Events.
"""

import json
import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from backend.api.deps import get_pipeline, get_session_store
from backend.core.rag_pipeline import RAGPipeline
from backend.core.session_store import SessionStore

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
