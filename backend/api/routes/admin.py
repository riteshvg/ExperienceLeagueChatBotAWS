"""
Admin endpoints — /api/admin/*

Authentication: POST /api/admin/login returns a short-lived JWT.
All other admin endpoints require that token as a Bearer header.
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import jwt
from pydantic import BaseModel

# project root
_ROOT = Path(__file__).parent.parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.api.deps import get_admin_user, get_retriever, _secret, _ALGORITHM
from src.utils.citation_mapper import _citation_stats

router = APIRouter(prefix="/admin")

_TOKEN_TTL_HOURS = 1


# ── Auth ─────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    password: str


@router.post("/login")
async def login(body: LoginRequest):
    admin_password = os.getenv("ADMIN_PASSWORD", "")
    if not admin_password or body.password != admin_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password",
        )
    exp = datetime.now(tz=timezone.utc) + timedelta(hours=_TOKEN_TTL_HOURS)
    token = jwt.encode(
        {"sub": "admin", "exp": exp},
        _secret(),
        algorithm=_ALGORITHM,
    )
    return {"token": token, "expires_at": exp.isoformat()}


@router.post("/logout")
async def logout(_: Annotated[str, Depends(get_admin_user)]):
    # JWT is stateless — client just discards the token
    return {"logged_out": True}


# ── Protected endpoints ───────────────────────────────────────────────────────

@router.get("/status")
async def system_status(
    request: Request,
    _: Annotated[str, Depends(get_admin_user)],
):
    retriever = get_retriever(request)
    chroma_stats = retriever.collection_stats()

    # Component health
    bedrock_ok = True
    try:
        import boto3
        boto3.client("bedrock-runtime", region_name=os.getenv("BEDROCK_REGION", "us-east-1"))
    except Exception:
        bedrock_ok = False

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
    }


@router.get("/settings")
async def get_settings_view(_: Annotated[str, Depends(get_admin_user)]):
    """Return non-sensitive configuration values."""
    cfg = {
        "bedrock_model_id": os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-3-7-sonnet-20250219-v1:0"),
        "bedrock_region": os.getenv("BEDROCK_REGION", "us-east-1"),
        "similarity_threshold": float(os.getenv("SIMILARITY_THRESHOLD", "0.6")),
        "max_retrieval_results": int(os.getenv("MAX_RETRIEVAL_RESULTS", "8")),
        "min_retrieval_results": int(os.getenv("MIN_RETRIEVAL_RESULTS", "3")),
        "query_enhancement_enabled": os.getenv("QUERY_ENHANCEMENT_ENABLED", "true").lower() == "true",
        "environment": os.getenv("ENVIRONMENT", "development"),
    }
    return cfg


@router.get("/analytics")
async def analytics(
    request: Request,
    _: Annotated[str, Depends(get_admin_user)],
):
    """Return basic in-process analytics (extend with DB queries as needed)."""
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
