"""
Minimal OAuth 2.0 authorization server for Claude.ai MCP connector.

Claude.ai requires OAuth to authenticate users before connecting to a custom
MCP server. This implements a single-user auto-approve flow — no real user
management, just a gate that issues a token after the user confirms.

Endpoints:
  GET  /.well-known/oauth-authorization-server  — OAuth metadata discovery
  POST /oauth/register                          — Dynamic client registration
  GET  /oauth/authorize                         — Authorization (shows approve page)
  POST /oauth/token                             — Token exchange
"""

import os
import secrets
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

_ROOT = Path(__file__).parent.parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.api.deps import _secret, _ALGORITHM
from jose import jwt

router = APIRouter()

# In-memory stores (fine for single-user personal tool)
_auth_codes: dict[str, dict] = {}      # code → {client_id, redirect_uri, ...}
_clients: dict[str, dict] = {}         # client_id → {redirect_uris, ...}

_TOKEN_TTL_DAYS = 30


def _issue_token(subject: str = "mcp-user") -> str:
    exp = datetime.now(tz=timezone.utc) + timedelta(days=_TOKEN_TTL_DAYS)
    return jwt.encode(
        {"sub": subject, "role": "mcp", "exp": exp},
        _secret(),
        algorithm=_ALGORITHM,
    )


# ── OAuth discovery ────────────────────────────────────────────────────────────

def _oauth_metadata(base: str) -> dict:
    return {
        "issuer": base,
        "authorization_endpoint": f"{base}/oauth/authorize",
        "token_endpoint": f"{base}/oauth/token",
        "registration_endpoint": f"{base}/register",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code"],
        "code_challenge_methods_supported": ["S256", "plain"],
        "token_endpoint_auth_methods_supported": ["none"],
        "scopes_supported": ["mcp"],
    }


@router.get("/.well-known/oauth-authorization-server")
async def oauth_metadata(request: Request):
    base = str(request.base_url).rstrip("/")
    return JSONResponse(_oauth_metadata(base))


@router.get("/.well-known/oauth-authorization-server/{path:path}")
async def oauth_metadata_path(request: Request, path: str):
    """Handle path-specific OAuth metadata (e.g. /.well-known/oauth-authorization-server/mcp/sse)."""
    base = str(request.base_url).rstrip("/")
    return JSONResponse(_oauth_metadata(base))


@router.get("/.well-known/oauth-protected-resource")
@router.get("/.well-known/oauth-protected-resource/{path:path}")
async def oauth_protected_resource(request: Request, path: str = ""):
    """Resource server metadata — tells Claude.ai which auth server to use."""
    base = str(request.base_url).rstrip("/")
    return JSONResponse({
        "resource": base,
        "authorization_servers": [base],
        "bearer_methods_supported": ["header"],
        "resource_documentation": f"{base}/mcp/sse",
    })


# ── Dynamic client registration ───────────────────────────────────────────────

@router.post("/register")           # Claude.ai hits /register directly
@router.post("/oauth/register")     # Also support /oauth/register
async def register_client(request: Request):
    body = await request.json()
    client_id = secrets.token_urlsafe(16)
    _clients[client_id] = {
        "redirect_uris": body.get("redirect_uris", []),
        "client_name": body.get("client_name", "Claude.ai"),
    }
    return JSONResponse({
        "client_id": client_id,
        "client_secret": "",          # public client
        "redirect_uris": _clients[client_id]["redirect_uris"],
        "token_endpoint_auth_method": "none",
    })


# ── Authorization endpoint ────────────────────────────────────────────────────

@router.get("/oauth/authorize", response_class=HTMLResponse)
async def authorize(
    request: Request,
    client_id: str = "",
    redirect_uri: str = "",
    state: str = "",
    code_challenge: str = "",
    code_challenge_method: str = "S256",
    response_type: str = "code",
):
    site_password = os.getenv("SITE_PASSWORD", "")
    return HTMLResponse(f"""
<!doctype html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Connect — Experience League Chatbot</title>
  <style>
    body {{ font-family: -apple-system, sans-serif; background: #f8fafc;
           display: flex; align-items: center; justify-content: center;
           min-height: 100vh; margin: 0; }}
    .card {{ background: white; border-radius: 16px; border: 1px solid #e2e8f0;
             box-shadow: 0 4px 16px rgba(0,0,0,.08); padding: 40px;
             width: 100%; max-width: 380px; }}
    .logo {{ width: 48px; height: 48px; border-radius: 12px;
             background: linear-gradient(135deg, #3b82f6, #8b5cf6);
             display: flex; align-items: center; justify-content: center;
             color: white; font-weight: 700; font-size: 18px;
             margin: 0 auto 16px; }}
    h1 {{ text-align: center; font-size: 18px; color: #1e293b; margin: 0 0 8px; }}
    p  {{ text-align: center; color: #64748b; font-size: 14px; margin: 0 0 24px; }}
    label {{ display: block; font-size: 13px; font-weight: 500;
             color: #475569; margin-bottom: 6px; }}
    input {{ width: 100%; padding: 10px 12px; border: 1px solid #e2e8f0;
             border-radius: 8px; font-size: 14px; box-sizing: border-box;
             outline: none; }}
    input:focus {{ border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59,130,246,.15); }}
    button {{ width: 100%; padding: 11px; background: #3b82f6; color: white;
              border: none; border-radius: 8px; font-size: 14px; font-weight: 600;
              cursor: pointer; margin-top: 16px; }}
    button:hover {{ background: #2563eb; }}
    .note {{ font-size: 12px; color: #94a3b8; text-align: center; margin-top: 16px; }}
  </style>
</head>
<body>
<div class="card">
  <div class="logo">EL</div>
  <h1>Experience League Chatbot</h1>
  <p>Claude.ai wants to search Adobe Experience League documentation.</p>
  <form method="POST" action="/oauth/approve">
    <input type="hidden" name="client_id" value="{client_id}">
    <input type="hidden" name="redirect_uri" value="{redirect_uri}">
    <input type="hidden" name="state" value="{state}">
    <input type="hidden" name="code_challenge" value="{code_challenge}">
    <input type="hidden" name="code_challenge_method" value="{code_challenge_method}">
    <label>Password</label>
    <input type="password" name="password" placeholder="Enter your password" autofocus>
    <button type="submit">Approve Access</button>
  </form>
  <p class="note">Unofficial tool · Not affiliated with Adobe</p>
</div>
</body>
</html>
""")


@router.post("/oauth/approve")
async def approve(
    client_id: str = Form(""),
    redirect_uri: str = Form(""),
    state: str = Form(""),
    code_challenge: str = Form(""),
    code_challenge_method: str = Form("S256"),
    password: str = Form(""),
):
    site_password = os.getenv("SITE_PASSWORD", "")
    if not site_password or password != site_password:
        raise HTTPException(status_code=401, detail="Invalid password")

    code = secrets.token_urlsafe(32)
    _auth_codes[code] = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
    }

    params = {"code": code}
    if state:
        params["state"] = state
    return RedirectResponse(f"{redirect_uri}?{urlencode(params)}", status_code=302)


# ── Token endpoint ────────────────────────────────────────────────────────────

@router.post("/oauth/token")
async def token(
    grant_type: str = Form(""),
    code: str = Form(""),
    redirect_uri: str = Form(""),
    client_id: str = Form(""),
    code_verifier: Optional[str] = Form(None),
):
    if grant_type != "authorization_code":
        raise HTTPException(status_code=400, detail="unsupported_grant_type")

    stored = _auth_codes.pop(code, None)
    if not stored:
        raise HTTPException(status_code=400, detail="invalid_grant")

    access_token = _issue_token()
    return JSONResponse({
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": _TOKEN_TTL_DAYS * 86400,
        "scope": "mcp",
    })
