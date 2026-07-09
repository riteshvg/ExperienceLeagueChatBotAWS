"""
Conversation history — GET /conversations, GET /conversations/{id}/messages

Pure reads from PostgreSQL. Loading a past conversation never calls the RAG
pipeline, embeddings, or the LLM — it's a database read only.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status as http_status

from backend.api.deps import get_site_user
from backend.core import google_db

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/conversations")
async def list_conversations(user: Annotated[dict, Depends(get_site_user)]):
    """The authenticated user's conversations, most recent first. Titles only — no message content."""
    uid = user.get("uid", "")
    try:
        conversations = google_db.list_conversations(uid)
    except Exception as e:
        logger.warning(f"list_conversations failed: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="History temporarily unavailable",
        )
    return {"conversations": conversations}


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str,
    user: Annotated[dict, Depends(get_site_user)],
):
    """Full transcript for one conversation. 404s for a missing id and for one
    owned by a different user identically — never confirm existence either way.
    """
    uid = user.get("uid", "")
    try:
        messages = google_db.get_conversation_messages(conversation_id, uid)
    except Exception as e:
        logger.warning(f"get_conversation_messages failed: {e}")
        messages = None
    if messages is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Not found")
    return {"conversation_id": conversation_id, "messages": messages}
