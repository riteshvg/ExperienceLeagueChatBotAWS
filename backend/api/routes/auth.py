"""
Site authentication — POST /api/auth/login

Authenticates against the users SQLite table (backend/core/user_db.py).
Credentials are seeded from SITE_USERNAME/SITE_PASSWORD env vars on first startup.
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from pydantic import BaseModel
from typing import Annotated, Optional

_ROOT = Path(__file__).parent.parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.api.deps import _secret, _ALGORITHM, get_site_user
from backend.core.demo_counter import get_status as global_demo_status
from backend.core import user_db

router = APIRouter(prefix="/auth")

_TOKEN_TTL_DAYS = 30


class SiteLoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
async def site_login(body: SiteLoginRequest):
    user = user_db.get_user_by_username(body.username)

    if not user or not user_db.verify_password(body.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been disabled. Contact the administrator.",
        )

    role = user["role"]
    ttl_days = 1 if role == "demo" else _TOKEN_TTL_DAYS
    exp = datetime.now(tz=timezone.utc) + timedelta(days=ttl_days)

    token = jwt.encode(
        {"sub": user["username"], "role": role, "uid": user["id"], "exp": exp},
        _secret(),
        algorithm=_ALGORITHM,
    )

    resp: dict = {"token": token, "role": role, "expires_at": exp.isoformat()}

    if role == "demo":
        # Return global demo counter so frontend shows the limit banner
        resp["demo"] = global_demo_status()
    elif user.get("question_limit") is not None:
        # Return per-user limit status so the same banner shows for limited users
        ql = user["question_limit"]
        qc = user["question_count"]
        resp["demo"] = {
            "questions_used": qc,
            "questions_limit": ql,
            "questions_remaining": max(0, ql - qc),
            "exhausted": qc >= ql,
        }

    return resp


@router.get("/demo/status")
async def get_demo_status():
    """Public endpoint — lets the frontend poll the global demo counter."""
    return global_demo_status()


@router.get("/status")
async def get_user_status(user: Annotated[dict, Depends(get_site_user)]):
    """Return current question-limit status for the authenticated user."""
    uid = user.get("uid")
    if not uid:
        return {"question_limit": None, "question_count": 0, "exhausted": False}
    db_user = user_db.get_user_by_id(uid)
    if not db_user:
        return {"question_limit": None, "question_count": 0, "exhausted": False}
    ql: Optional[int] = db_user.get("question_limit")
    qc: int = db_user.get("question_count", 0)
    if ql is None:
        return {"question_limit": None, "question_count": qc, "exhausted": False}
    return {
        "questions_used": qc,
        "questions_limit": ql,
        "questions_remaining": max(0, ql - qc),
        "exhausted": qc >= ql,
    }
