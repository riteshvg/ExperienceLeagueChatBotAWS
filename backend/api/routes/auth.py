"""
Site authentication — POST /api/auth/login

Separate from admin auth. Controls access to the chatbot for public visitors.
Credentials: SITE_USERNAME + SITE_PASSWORD in .env
Token TTL: 30 days (so the user doesn't have to log in daily)
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from jose import jwt
from pydantic import BaseModel

_ROOT = Path(__file__).parent.parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.api.deps import _secret, _ALGORITHM
from config.settings import get_settings

router = APIRouter(prefix="/auth")

_TOKEN_TTL_DAYS = 30


class SiteLoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
async def site_login(body: SiteLoginRequest):
    s = get_settings()
    site_username = s.site_username or ""
    site_password = s.site_password or ""

    if not site_username or not site_password:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Site credentials not configured",
        )

    if body.username != site_username or body.password != site_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    exp = datetime.now(tz=timezone.utc) + timedelta(days=_TOKEN_TTL_DAYS)
    token = jwt.encode(
        {"sub": body.username, "role": "user", "exp": exp},
        _secret(),
        algorithm=_ALGORITHM,
    )
    return {"token": token, "expires_at": exp.isoformat()}
