"""
Conversation persistence endpoints — /api/conversations

Server-side backing store for chat history, keyed to the Google OAuth
user_id. All routes require an authenticated session; there is no public
route yet (see Phase 1 plan — sharing is a separate follow-up).
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.api.deps import get_site_user
from backend.core import google_db

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/conversations")
async def list_conversations(user: Annotated[dict, Depends(get_site_user)]):
    uid = user.get("uid")
    return {"conversations": google_db.list_conversations(uid)}


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: int, user: Annotated[dict, Depends(get_site_user)]):
    uid = user.get("uid")
    conversation = google_db.get_conversation(conversation_id, uid)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


class RenameRequest(BaseModel):
    title: str


@router.patch("/conversations/{conversation_id}")
async def rename_conversation(
    conversation_id: int,
    body: RenameRequest,
    user: Annotated[dict, Depends(get_site_user)],
):
    uid = user.get("uid")
    updated = google_db.rename_conversation(conversation_id, uid, body.title)
    if updated is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return updated


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: int, user: Annotated[dict, Depends(get_site_user)]):
    uid = user.get("uid")
    deleted = google_db.delete_conversation(conversation_id, uid)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"deleted": True}
