"""Shared FastAPI dependencies."""

import os
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from jose import JWTError, jwt

_ALGORITHM = "HS256"
_security = HTTPBearer(auto_error=False)


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
    """Validate Bearer JWT token. Returns {"sub": username, "role": "user"|"demo"}."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(
            credentials.credentials, _secret(), algorithms=[_ALGORITHM]
        )
        sub: str = payload.get("sub", "")
        role: str = payload.get("role", "user")
        exp: int = payload.get("exp", 0)
        if not sub or datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(tz=timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired"
            )
        return {"sub": sub, "role": role}
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )


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
        return sub
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )
