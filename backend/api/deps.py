"""Shared FastAPI dependencies."""

import logging
import os
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from jose import JWTError, jwt

_ALGORITHM = "HS256"
_security = HTTPBearer(auto_error=False)

logger = logging.getLogger(__name__)


def _secret() -> str:
    secret = os.getenv("ADMIN_SECRET_KEY", "")
    if not secret:
        # Fall back to ADMIN_PASSWORD so existing .env files work
        secret = os.getenv("ADMIN_PASSWORD", "changeme-set-ADMIN_SECRET_KEY")
    return secret


def get_retriever(request: Request):
    return request.app.state.retriever


def get_session_store(request: Request):
    return request.app.state.session_store


def get_pipeline(request: Request):
    return request.app.state.pipeline


def get_site_user(
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials], Depends(_security)
    ] = None,
) -> dict:
    """Validate Bearer session token against PostgreSQL exl_sessions table.

    Returns {"sub": email, "role": "user", "uid": google_sub, "email": email}.
    Raises 401 with a user-friendly message if the session is missing or expired.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sign in with Google to use EXL Chatbot.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        from backend.core import google_db
        session = google_db.get_session(credentials.credentials)
    except RuntimeError as exc:
        # google_db unavailable (no PostgreSQL configured)
        logger.error(f"google_db unavailable: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable. Check DATABASE_URL configuration.",
        )
    except Exception as exc:
        logger.error(f"Session lookup failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service temporarily unavailable.",
        )

    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sign in with Google to use EXL Chatbot.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if session.get("is_disabled"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your access has been disabled. Please contact the administrator.",
        )

    return {
        "sub": session["email"],
        "role": "user",
        "uid": session["user_id"],
        "email": session["email"],
        "name": session.get("name", ""),
    }


def get_admin_user(
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials], Depends(_security)
    ] = None,
) -> str:
    """Validate Bearer JWT token issued by /api/admin/login."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
        )
    try:
        payload = jwt.decode(
            credentials.credentials, _secret(), algorithms=[_ALGORITHM]
        )
        sub: str = payload.get("sub", "")
        exp: int = payload.get("exp", 0)
        if not sub or datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(tz=timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired"
            )
        # If ADMIN_EMAIL is set, only that email may use the admin panel
        admin_email = os.getenv("ADMIN_EMAIL", "").strip().lower()
        if admin_email and sub.strip().lower() != admin_email:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Admin access restricted"
            )
        return sub
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )
