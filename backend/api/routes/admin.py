"""
Admin endpoints — /api/admin/*

Authentication: POST /api/admin/login returns a short-lived JWT.
All other admin endpoints require that token as a Bearer header.
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import jwt
from pydantic import BaseModel

_ROOT = Path(__file__).parent.parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.api.deps import get_admin_user, get_retriever, _secret, _ALGORITHM
from backend.core import user_db as _user_db
from config.settings import get_settings

router = APIRouter(prefix="/admin")

_TOKEN_TTL_HOURS = 1
_FEEDBACK_FILE = _ROOT / "data" / "feedback.jsonl"

# Citation stats are no longer tracked (citation_mapper removed); return empty.
_citation_stats: dict = {}


# ── Admin auth ────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    password: str


@router.post("/login")
async def login(body: LoginRequest):
    admin_password = get_settings().admin_password or ""
    if not admin_password or body.password != admin_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")
    exp = datetime.now(tz=timezone.utc) + timedelta(hours=_TOKEN_TTL_HOURS)
    token = jwt.encode({"sub": "admin", "exp": exp}, _secret(), algorithm=_ALGORITHM)
    return {"token": token, "expires_at": exp.isoformat()}


@router.post("/logout")
async def logout(_: Annotated[str, Depends(get_admin_user)]):
    return {"logged_out": True}


# ── User management ───────────────────────────────────────────────────────────

class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str = "user"
    question_limit: Optional[int] = None
    is_active: bool = True


class UpdateUserRequest(BaseModel):
    password: Optional[str] = None
    role: Optional[str] = None
    question_limit: Optional[int] = None
    is_active: Optional[bool] = None


def _safe_user(u: dict) -> dict:
    """Strip password_hash before returning to client."""
    return {k: v for k, v in u.items() if k != "password_hash"}


def _enrich_user(u: dict) -> dict:
    """Add total_cost to a user record."""
    enriched = _safe_user(u)
    enriched["total_cost_usd"] = _user_db.get_user_total_cost(u["id"])
    return enriched


@router.get("/users")
async def list_users(_: Annotated[str, Depends(get_admin_user)]):
    users = _user_db.list_users()
    return [_enrich_user(u) for u in users]


@router.post("/users", status_code=201)
async def create_user(
    body: CreateUserRequest,
    _: Annotated[str, Depends(get_admin_user)],
):
    if _user_db.get_user_by_username(body.username):
        raise HTTPException(status_code=409, detail="Username already exists")
    if body.role not in ("user", "demo"):
        raise HTTPException(status_code=422, detail="role must be 'user' or 'demo'")
    user = _user_db.create_user(
        username=body.username,
        password=body.password,
        role=body.role,
        question_limit=body.question_limit,
        is_active=body.is_active,
    )
    return _safe_user(user)


@router.patch("/users/{user_id}")
async def update_user(
    user_id: int,
    body: UpdateUserRequest,
    _: Annotated[str, Depends(get_admin_user)],
):
    if not _user_db.get_user_by_id(user_id):
        raise HTTPException(status_code=404, detail="User not found")
    if body.role is not None and body.role not in ("user", "demo"):
        raise HTTPException(status_code=422, detail="role must be 'user' or 'demo'")

    # Build kwargs from explicitly-provided fields (model_fields_set)
    kwargs: dict = {}
    provided = body.model_fields_set
    if "password" in provided and body.password:
        kwargs["password"] = body.password
    if "role" in provided and body.role is not None:
        kwargs["role"] = body.role
    if "question_limit" in provided:
        kwargs["question_limit"] = body.question_limit  # None clears the limit
    if "is_active" in provided and body.is_active is not None:
        kwargs["is_active"] = body.is_active

    user = _user_db.update_user(user_id, **kwargs)
    return _safe_user(user)


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    _: Annotated[str, Depends(get_admin_user)],
):
    if not _user_db.delete_user(user_id):
        raise HTTPException(status_code=404, detail="User not found")


@router.get("/users/{user_id}/usage")
async def get_user_usage(
    user_id: int,
    _: Annotated[str, Depends(get_admin_user)],
):
    if not _user_db.get_user_by_id(user_id):
        raise HTTPException(status_code=404, detail="User not found")
    logs = _user_db.get_user_usage(user_id)
    total_cost = sum(l.get("total_cost_usd", 0) for l in logs)
    return {"user_id": user_id, "logs": logs, "total_cost_usd": total_cost}


@router.get("/users/{user_id}/feedback")
async def get_user_feedback(
    user_id: int,
    _: Annotated[str, Depends(get_admin_user)],
):
    import json as _json
    user = _user_db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Feedback is stored by session; match on username via session lookup is not
    # directly available, so we return all feedback with the session_id for context.
    # Future: join feedback on user sessions when session ownership is tracked.
    entries = []
    if _FEEDBACK_FILE.exists():
        for line in _FEEDBACK_FILE.read_text().strip().splitlines():
            try:
                entries.append(_json.loads(line))
            except Exception:
                pass
    return {"user_id": user_id, "username": user["username"], "entries": entries}


# ── Refresh pipeline ──────────────────────────────────────────────────────────

@router.get("/refresh/status")
async def refresh_status(_: Annotated[str, Depends(get_admin_user)]):
    from backend.core.refresh_pipeline import get_status
    return get_status()


@router.post("/refresh/start")
async def refresh_start(_: Annotated[str, Depends(get_admin_user)], force: bool = False):
    from backend.core.refresh_pipeline import trigger_refresh
    return trigger_refresh(force=force)


@router.post("/refresh/trigger-actions")
async def trigger_github_actions(_: Annotated[str, Depends(get_admin_user)], force: bool = False):
    import httpx
    token = os.getenv("GITHUB_TOKEN", "")
    if not token:
        raise HTTPException(status_code=503, detail="GITHUB_TOKEN not configured")
    url = "https://api.github.com/repos/riteshvg/ExperienceLeagueChatBotAWS/actions/workflows/refresh-docs.yml/dispatches"
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url,
            json={"ref": "main", "inputs": {"force": "true" if force else "false"}},
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"},
            timeout=15,
        )
    if resp.status_code == 204:
        return {"triggered": True, "message": "GitHub Actions workflow dispatched"}
    raise HTTPException(status_code=resp.status_code, detail=f"GitHub API error: {resp.text}")


# ── Feedback ──────────────────────────────────────────────────────────────────

@router.get("/feedback")
async def get_feedback(_: Annotated[str, Depends(get_admin_user)]):
    import json as _json
    entries = []
    if _FEEDBACK_FILE.exists():
        for line in _FEEDBACK_FILE.read_text().strip().splitlines():
            try:
                entries.append(_json.loads(line))
            except Exception:
                pass
    total = len(entries)
    thumbs_up = sum(1 for e in entries if e.get("rating") == 1)
    thumbs_down = sum(1 for e in entries if e.get("rating") == -1)
    return {
        "summary": {
            "total": total,
            "thumbs_up": thumbs_up,
            "thumbs_down": thumbs_down,
            "positive_pct": round(thumbs_up / total * 100, 1) if total else 0,
        },
        "entries": sorted(entries, key=lambda e: e.get("timestamp", ""), reverse=True)[:50],
    }


# ── Demo ──────────────────────────────────────────────────────────────────────

@router.post("/demo/reset")
async def reset_demo(_: Annotated[str, Depends(get_admin_user)]):
    from backend.core.demo_counter import reset as demo_reset
    # Also reset the demo user's question_count in the DB
    demo_user = _user_db.get_user_by_username("demo")
    if demo_user:
        _user_db.update_user(demo_user["id"], question_count=0)
    return demo_reset()


@router.get("/demo/status")
async def demo_status_admin(_: Annotated[str, Depends(get_admin_user)]):
    from backend.core.demo_counter import get_status
    return get_status()


# ── System status ─────────────────────────────────────────────────────────────

@router.get("/status")
async def system_status(request: Request, _: Annotated[str, Depends(get_admin_user)]):
    retriever = get_retriever(request)
    chroma_stats = retriever.collection_stats()
    product_breakdown = retriever.product_breakdown()

    bedrock_ok = True
    try:
        import boto3
        boto3.client("bedrock-runtime", region_name=os.getenv("BEDROCK_REGION", "us-east-1"))
    except Exception:
        bedrock_ok = False

    from backend.core.refresh_pipeline import get_status as get_refresh_status
    rs = get_refresh_status()

    return {
        "components": {
            "chromadb": {"healthy": True, **chroma_stats},
            "bedrock": {"healthy": bedrock_ok},
            "session_store": {
                "healthy": True,
                "active_sessions": len(request.app.state.session_store.list_sessions()),
            },
        },
        "citation_stats": dict(_citation_stats),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "knowledge_base": {
            "last_refreshed": rs.get("last_run"),
            "total_chunks": chroma_stats.get("document_count", 0),
            "product_breakdown": product_breakdown,
        },
    }


@router.get("/settings")
async def get_settings_view(_: Annotated[str, Depends(get_admin_user)]):
    return {
        "bedrock_model_id": os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0"),
        "bedrock_region": os.getenv("BEDROCK_REGION", "us-east-1"),
        "similarity_threshold": float(os.getenv("SIMILARITY_THRESHOLD", "0.6")),
        "max_retrieval_results": int(os.getenv("MAX_RETRIEVAL_RESULTS", "8")),
        "min_retrieval_results": int(os.getenv("MIN_RETRIEVAL_RESULTS", "3")),
        "query_enhancement_enabled": os.getenv("QUERY_ENHANCEMENT_ENABLED", "true").lower() == "true",
        "environment": os.getenv("ENVIRONMENT", "development"),
    }


@router.get("/analytics")
async def analytics(request: Request, _: Annotated[str, Depends(get_admin_user)]):
    sessions = request.app.state.session_store.list_sessions()
    total_turns = sum(
        len(request.app.state.session_store.get_history(s)) // 2
        for s in sessions
    )
    return {
        "active_sessions": len(sessions),
        "total_turns": total_turns,
        "citation_registry_hits": _citation_stats.get("registry_hits", 0),
        "citation_fallback_misses": _citation_stats.get("fallback_misses", 0),
    }
