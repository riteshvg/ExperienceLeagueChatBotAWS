"""
Google OAuth endpoints.

GET    /api/auth/google           — redirect browser to Google consent screen
GET    /api/auth/google/callback  — exchange auth code, create session, redirect to frontend
DELETE /api/auth/session          — invalidate session (logout)
"""

import logging
import sys
from pathlib import Path
from typing import Annotated
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse

_ROOT = Path(__file__).parent.parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.api.deps import get_site_user
from backend.core import google_db
from config.settings import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth")

_GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v1/userinfo"


def _s():
    return get_settings()


def _error_redirect(frontend_url: str, reason: str) -> RedirectResponse:
    return RedirectResponse(f"{frontend_url}/callback?error={reason}")


@router.get("/google")
async def google_login(request: Request):
    """Redirect to Google OAuth consent screen."""
    s = _s()
    if not s.google_client_id or not s.oauth_redirect_uri:
        raise HTTPException(status_code=503, detail="Google OAuth not configured on this server.")

    ip = request.headers.get("x-forwarded-for", request.client.host or "unknown").split(",")[0].strip()
    try:
        if not google_db.check_and_update_ratelimit(ip):
            raise HTTPException(status_code=429, detail="Too many sign-in attempts. Try again in a minute.")
    except RuntimeError:
        # DB unavailable — still allow the redirect (fail open on rate limit)
        pass

    params = urlencode({
        "client_id": s.google_client_id,
        "redirect_uri": s.oauth_redirect_uri,
        "response_type": "code",
        "scope": "email profile openid",
        "access_type": "online",
        "prompt": "select_account",
    })
    return RedirectResponse(f"{_GOOGLE_AUTH_URL}?{params}")


@router.get("/google/callback")
async def google_callback(
    request: Request,
    code: str = None,
    error: str = None,
):
    """Exchange auth code for tokens, upsert user, create session, redirect to frontend."""
    s = _s()
    frontend = s.frontend_url

    if error or not code:
        logger.warning(f"OAuth denied or missing code: error={error}")
        return _error_redirect(frontend, "oauth_denied")

    # Exchange code for tokens
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            token_resp = await client.post(
                _GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": s.google_client_id,
                    "client_secret": s.google_client_secret,
                    "redirect_uri": s.oauth_redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
    except Exception as exc:
        logger.error(f"Token exchange network error: {exc}")
        return _error_redirect(frontend, "token_exchange_failed")

    if token_resp.status_code != 200:
        logger.error(f"Token exchange failed: {token_resp.status_code} {token_resp.text}")
        return _error_redirect(frontend, "token_exchange_failed")

    access_token = token_resp.json().get("access_token")
    if not access_token:
        return _error_redirect(frontend, "no_access_token")

    # Fetch Google user info
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            user_resp = await client.get(
                _GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
    except Exception as exc:
        logger.error(f"Userinfo fetch error: {exc}")
        return _error_redirect(frontend, "userinfo_failed")

    if user_resp.status_code != 200:
        return _error_redirect(frontend, "userinfo_failed")

    info = user_resp.json()
    user_id = info.get("id", "")
    email = info.get("email", "")
    name = info.get("name", email)
    picture = info.get("picture", "")

    if not user_id or not email:
        return _error_redirect(frontend, "missing_user_info")

    # Persist user + create session
    try:
        user_row = google_db.upsert_user(user_id, email, name, picture)
        session_token, expires_at = google_db.create_session(user_id, email, name, picture)
    except Exception as exc:
        logger.error(f"DB error during session creation: {exc}")
        return _error_redirect(frontend, "db_error")

    is_admin = bool(user_row.get("is_admin", False))

    # Redirect to frontend /callback with session data as query params
    params = urlencode({
        "token": session_token,
        "user_id": user_id,
        "email": email,
        "name": name,
        "picture": picture,
        "expires_at": expires_at,
        "is_admin": "1" if is_admin else "0",
    })
    return RedirectResponse(f"{frontend}/callback?{params}")


@router.get("/me")
async def get_me(user: Annotated[dict, Depends(get_site_user)]):
    """Return current user's daily usage info."""
    uid = user.get("uid", "")
    usage: dict = {"queries_used": 0, "queries_limit": 20, "queries_remaining": 20}
    if uid:
        try:
            usage = google_db.get_usage_info(uid)
        except Exception:
            pass
    return {
        "user_id": uid,
        "email": user.get("email", ""),
        "name": user.get("name", ""),
        **usage,
    }


@router.delete("/session")
async def logout(request: Request):
    """Invalidate the caller's session on the server."""
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
        try:
            google_db.delete_session(token)
        except Exception as exc:
            logger.warning(f"Session delete failed (non-fatal): {exc}")
    return {"logged_out": True}
