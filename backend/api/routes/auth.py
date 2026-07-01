"""
OAuth endpoints.

GET    /api/auth/google           — redirect browser to Google consent screen
GET    /api/auth/google/callback  — exchange auth code, create session, redirect to frontend
GET    /api/auth/github           — redirect browser to GitHub consent screen
GET    /api/auth/github/callback  — exchange auth code, create session, redirect to frontend
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
_GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
_GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
_GITHUB_USER_URL = "https://api.github.com/user"
_GITHUB_EMAILS_URL = "https://api.github.com/user/emails"


def _s():
    return get_settings()


def _error_redirect(frontend_url: str, reason: str) -> RedirectResponse:
    return RedirectResponse(f"{frontend_url}/callback?error={reason}")


def _session_redirect(
    frontend_url: str,
    user_id: str,
    email: str,
    name: str,
    picture: str,
) -> RedirectResponse:
    try:
        user_row = google_db.upsert_user(user_id, email, name, picture)
        canonical_user_id = user_row.get("user_id", user_id)
        session_token, expires_at = google_db.create_session(canonical_user_id, email, name, picture)
    except Exception as exc:
        logger.error(f"DB error during session creation: {exc}")
        return _error_redirect(frontend_url, "db_error")

    is_admin = bool(user_row.get("is_admin", False))
    params = urlencode({
        "token": session_token,
        "user_id": canonical_user_id,
        "email": email,
        "name": name,
        "picture": picture,
        "expires_at": expires_at,
        "is_admin": "1" if is_admin else "0",
    })
    return RedirectResponse(f"{frontend_url}/callback?{params}")


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

    return _session_redirect(frontend, user_id, email, name, picture)


@router.get("/github")
async def github_login(request: Request):
    """Redirect to GitHub OAuth consent screen."""
    s = _s()
    if not s.github_client_id or not s.github_oauth_redirect_uri:
        raise HTTPException(status_code=503, detail="GitHub OAuth not configured on this server.")

    ip = request.headers.get("x-forwarded-for", request.client.host or "unknown").split(",")[0].strip()
    try:
        if not google_db.check_and_update_ratelimit(ip):
            raise HTTPException(status_code=429, detail="Too many sign-in attempts. Try again in a minute.")
    except RuntimeError:
        pass

    params = urlencode({
        "client_id": s.github_client_id,
        "redirect_uri": s.github_oauth_redirect_uri,
        "scope": "read:user user:email",
    })
    return RedirectResponse(f"{_GITHUB_AUTH_URL}?{params}")


@router.get("/github/callback")
async def github_callback(
    request: Request,
    code: str = None,
    error: str = None,
):
    """Exchange GitHub auth code for tokens, upsert user, create session, redirect to frontend."""
    s = _s()
    frontend = s.frontend_url

    if error or not code:
        logger.warning(f"GitHub OAuth denied or missing code: error={error}")
        return _error_redirect(frontend, "oauth_denied")

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            token_resp = await client.post(
                _GITHUB_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": s.github_client_id,
                    "client_secret": s.github_client_secret,
                    "redirect_uri": s.github_oauth_redirect_uri,
                },
                headers={"Accept": "application/json"},
            )
    except Exception as exc:
        logger.error(f"GitHub token exchange network error: {exc}")
        return _error_redirect(frontend, "token_exchange_failed")

    if token_resp.status_code != 200:
        logger.error(f"GitHub token exchange failed: {token_resp.status_code} {token_resp.text}")
        return _error_redirect(frontend, "token_exchange_failed")

    access_token = token_resp.json().get("access_token")
    if not access_token:
        return _error_redirect(frontend, "no_access_token")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            user_resp = await client.get(_GITHUB_USER_URL, headers=headers)
            emails_resp = await client.get(_GITHUB_EMAILS_URL, headers=headers)
    except Exception as exc:
        logger.error(f"GitHub userinfo fetch error: {exc}")
        return _error_redirect(frontend, "userinfo_failed")

    if user_resp.status_code != 200:
        logger.error(f"GitHub userinfo failed: {user_resp.status_code} {user_resp.text}")
        return _error_redirect(frontend, "userinfo_failed")

    info = user_resp.json()
    github_id = str(info.get("id") or "")
    email = info.get("email") or ""

    if not email and emails_resp.status_code == 200:
        emails = emails_resp.json()
        primary = next(
            (
                row for row in emails
                if row.get("primary") and row.get("verified") and row.get("email")
            ),
            None,
        )
        if primary:
            email = primary["email"]

    name = info.get("name") or info.get("login") or email
    picture = info.get("avatar_url") or ""

    if not github_id or not email:
        return _error_redirect(frontend, "missing_user_info")

    return _session_redirect(frontend, f"github:{github_id}", email, name, picture)


@router.get("/me")
async def get_me(user: Annotated[dict, Depends(get_site_user)]):
    """Return current user's daily and monthly usage info."""
    uid = user.get("uid", "")
    usage: dict = {"queries_used": 0, "queries_limit": 20, "queries_remaining": 20}
    monthly: dict = {"monthly_limit": 999999, "monthly_used": 0, "monthly_remaining": 999999, "reset_date": None, "is_new_user": False}
    if uid:
        try:
            usage = google_db.get_usage_info(uid)
        except Exception:
            pass
        try:
            monthly = google_db.get_monthly_quota_info(uid)
        except Exception:
            pass
    return {
        "user_id": uid,
        "email": user.get("email", ""),
        "name": user.get("name", ""),
        **usage,
        **monthly,
    }


@router.get("/quota")
async def get_quota(user: Annotated[dict, Depends(get_site_user)]):
    """Return current user's monthly quota state."""
    uid = user.get("uid", "")
    if not uid:
        from datetime import date as _date
        today = __import__('datetime').datetime.now().date()
        yr, mo = today.year, today.month
        from datetime import date as d
        reset = d(yr + 1, 1, 1).isoformat() if mo == 12 else d(yr, mo + 1, 1).isoformat()
        return {"monthly_limit": 999999, "monthly_used": 0, "monthly_remaining": 999999, "reset_date": reset, "is_new_user": False}
    try:
        return google_db.get_monthly_quota_info(uid)
    except Exception:
        return {"monthly_limit": 999999, "monthly_used": 0, "monthly_remaining": 999999, "reset_date": None, "is_new_user": False}


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
