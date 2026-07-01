"""
Chat endpoint — POST /api/chat

Streams tokens + citations back to the client using Server-Sent Events.
Usage tracking via google_db (total_queries counter on exl_users).
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Optional

from anthropic import AsyncAnthropic
from fastapi import APIRouter, Depends, HTTPException, Request, status as http_status
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from backend.api.deps import get_pipeline, get_session_store, get_site_user
from backend.core import google_db
from backend.core.landing_questions import build_landing_payload
from backend.core.rag_pipeline import RAGPipeline
from backend.core.session_store import SessionStore

_ROOT = Path(__file__).parent.parent.parent.parent
FEEDBACK_FILE = _ROOT / "data" / "feedback.jsonl"

logger = logging.getLogger(__name__)
router = APIRouter()

_NON_ENGLISH_MSG = (
    "For now, only English language questions are supported. "
    "Please rephrase your question in English and I'll be happy to help!"
)

# Words removed from this list because they are also common English words:
# was (German: what), hat (German: has), come (Italian: how), comment (French: how),
# con (Spanish: with), como/come (Spanish/Portuguese/Italian: how),
# quando/qual (Portuguese/Italian: when/which),
# pour (French: for) — English verb,
# par (French: by/through) — English noun (golf, "on par"),
# les (French: the) — English name/abbreviation,
# sur (French: on) — English prefix,
# nous (French: we) — English philosophical noun,
# para (Spanish: for) — English informal noun (paratrooper),
# hasta (Spanish: until) — in English dictionaries,
# ist (German: is) — in English dictionaries,
# sind (German: are) — in English dictionaries,
# nach (German: after) — in English dictionaries,
# quale (Italian: which) — English philosophical term (qualia).
# Rule for adding new words to this blocklist:
# 1. The word must NOT appear in an English dictionary
# 2. The word must NOT be a common English proper noun or prefix
# 3. When in doubt, leave it out — false positives are worse than false negatives
# 4. Split compound forms on hyphens before checking (puis-je → puis, je)
_NON_ENGLISH_WORDS = {
    # French — unambiguous, no English meaning
    "quelles", "quelle", "sont", "des", "pourquoi",
    "quand", "avec", "dans", "qui", "que", "une", "votre",
    "vous", "ils", "elles", "mais", "donc", "puis", "aussi", "comme",
    "dernières", "derniers", "fonctionnalités", "fonctionnalité",
    # Spanish — unambiguous or have accents (caught by non-ASCII check anyway)
    "cómo", "cuál", "cuáles", "qué", "cuándo", "dónde", "quién", "quiénes",
    "configurar", "configuración", "últimas", "últimos", "características",
    "desde", "tiene", "puede", "están",
    # German — unambiguous, no English meaning
    "wie", "wann", "warum", "welche", "welcher", "welches", "können",
    "haben", "mit", "von", "für", "über",
    "einrichten", "konfigurieren", "neuesten", "funktionen",
    # Italian — unambiguous
    "cosa", "perché", "quali", "configurare",
    "ultime", "funzionalità",
    # Portuguese — unambiguous
    "porque", "funcionalidades",
}


def _is_non_english(text: str) -> bool:
    """Detect non-English via accented chars or known non-English stopwords."""
    # 1. Any non-ASCII alphabetic character (é è ê ç ñ ü ä ō etc.) → non-English
    non_ascii_alpha = sum(1 for c in text if c.isalpha() and ord(c) > 127)
    if non_ascii_alpha >= 1:
        logger.info(f"[lang] non-ASCII alpha={non_ascii_alpha}, blocking: {text[:60]!r}")
        return True

    # 2. Check for unambiguous non-English words
    # Split on whitespace then hyphens so "puis-je" → {"puis", "je"}
    words = {
        part.lower().strip("?!.,;:'\"")
        for token in text.split()
        for part in token.split("-")
    }
    hit = words & _NON_ENGLISH_WORDS
    if hit:
        logger.info(f"[lang] non-English words={hit}, blocking: {text[:60]!r}")
        return True

    return False


class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    haiku_only: bool = False
    message_id: Optional[str] = None


@router.post("/chat")
async def chat(
    body: ChatRequest,
    pipeline: Annotated[RAGPipeline, Depends(get_pipeline)],
    session_store: Annotated[SessionStore, Depends(get_session_store)],
    user: Annotated[dict, Depends(get_site_user)],
):
    uid: Optional[str] = user.get("uid")
    session_id = body.session_id or session_store.new_session()

    # Check daily rate limit BEFORE starting the SSE stream
    if uid:
        try:
            rate_info = google_db.check_rate_limit(uid)
            if not rate_info["allowed"]:
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "rate_limit_exceeded",
                        "message": f"You have reached your daily limit of {rate_info['limit']} queries. Your limit resets at midnight UTC.",
                        "queries_used": rate_info["count"],
                        "queries_limit": rate_info["limit"],
                        "resets_at": "midnight UTC",
                    },
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Rate limit check failed (non-fatal): {e}")

    # Check monthly quota BEFORE starting the SSE stream
    if uid:
        try:
            monthly_info = google_db.check_monthly_quota(uid)
            if not monthly_info["allowed"]:
                raise HTTPException(
                    status_code=429,
                    detail="MONTHLY_QUOTA_EXCEEDED",
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Monthly quota check failed (non-fatal): {e}")

    # Language gate — before any LLM call
    if _is_non_english(body.query):
        if uid:
            try:
                google_db.log_query(
                    user_id=uid,
                    email=user.get("email", ""),
                    query_text=body.query,
                    llm_model="blocked:language",
                    input_tokens=0,
                    output_tokens=0,
                    message_id=body.message_id or "",
                )
                google_db.touch_last_seen(uid)
            except Exception as e:
                logger.warning(f"Language-blocked query logging failed (non-fatal): {e}")

        async def _non_english_gen():
            yield {"data": json.dumps({"type": "token", "content": _NON_ENGLISH_MSG})}
            yield {"data": json.dumps({"type": "citations", "citations": []})}
            yield {"data": json.dumps({"type": "done", "model": "none", "session_id": session_id,
                                       "input_tokens": 0, "output_tokens": 0})}
        return EventSourceResponse(_non_english_gen())

    async def event_generator():
        full_response = ""
        last_done: Optional[dict] = None

        async for event in pipeline.stream(
            query=body.query,
            session_id=session_id,
            haiku_only=body.haiku_only,
        ):
            if event["type"] == "token":
                full_response += event.get("content", "")
            elif event["type"] == "done":
                # Buffer the done event — augment it with usage info before yielding
                last_done = event
                continue
            yield {"data": json.dumps(event)}

        # After the pipeline loop: augment done event with usage counts, then yield it
        if last_done is not None:
            if uid:
                try:
                    usage = google_db.increment_daily_count(uid)
                    last_done = {
                        **last_done,
                        "queries_used": usage["count"],
                        "queries_remaining": max(0, usage["limit"] - usage["count"]),
                        "queries_limit": usage["limit"],
                    }
                except Exception as e:
                    logger.warning(f"Daily count increment failed (non-fatal): {e}")
                try:
                    google_db.increment_monthly_count(uid)
                except Exception as e:
                    logger.warning(f"Monthly count increment failed (non-fatal): {e}")
            yield {"data": json.dumps(last_done)}

        # After streaming: track usage + log query
        if uid and last_done:
            try:
                google_db.increment_total_queries(uid)
                google_db.touch_last_seen(uid)
                google_db.log_query(
                    user_id=uid,
                    email=user.get("email", ""),
                    query_text=body.query,
                    llm_model=last_done.get("model", "unknown"),
                    input_tokens=int(last_done.get("input_tokens", 0)),
                    output_tokens=int(last_done.get("output_tokens", 0)),
                    message_id=body.message_id or "",
                )
            except Exception as e:
                logger.warning(f"Usage tracking failed (non-fatal): {e}")

    return EventSourceResponse(event_generator())


@router.get("/chat/landing-questions")
async def landing_questions(_user: Annotated[dict, Depends(get_site_user)]):
    """Real user questions from PostgreSQL, grouped by Rovr solution."""
    try:
        rows = google_db.get_popular_query_logs(limit=200)
        return build_landing_payload(rows)
    except Exception as e:
        logger.warning(f"Landing questions fetch failed, using fallback: {e}")
        return build_landing_payload([])


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
    return {"session_id": session_store.new_session()}


class FollowUpsRequest(BaseModel):
    query: str
    answer: str


@router.post("/chat/follow-ups")
async def get_follow_ups(body: FollowUpsRequest, _user: Annotated[dict, Depends(get_site_user)]):
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
    rating: int
    query: str
    comment: str = ""


@router.post("/chat/feedback")
async def submit_feedback(body: FeedbackRequest, _user: Annotated[dict, Depends(get_site_user)]):
    try:
        google_db.log_feedback(
            message_id=body.message_id,
            user_id=_user.get("uid", ""),
            email=_user.get("email", ""),
            query_text=body.query,
            rating=body.rating,
            comment=body.comment,
        )
    except Exception as e:
        logger.warning(f"Feedback DB write failed (non-fatal): {e}")
        # Fallback to JSONL
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


@router.get("/ping")
async def ping():
    """Lightweight liveness probe — kill switch middleware intercepts this and returns 503 when disabled."""
    return {"ok": True}

