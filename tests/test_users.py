"""
Tests for user management: user_db helpers + admin API routes.

Run:  pytest tests/test_users.py -v
"""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# ── Isolate DB to a temp file per test ───────────────────────────────────────

@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Point user_db._DB_PATH at a fresh temp file for each test."""
    from backend.core import user_db as udb
    monkeypatch.setattr(udb, "_DB_PATH", tmp_path / "test_users.db")
    udb.init_db()
    yield


# ── user_db unit tests ────────────────────────────────────────────────────────

from backend.core import user_db as udb


def test_create_and_get_user():
    user = udb.create_user("alice", "secret")
    assert user["username"] == "alice"
    assert user["role"] == "user"
    assert user["is_active"] == 1
    assert "password_hash" in user

    fetched = udb.get_user_by_username("alice")
    assert fetched is not None
    assert fetched["id"] == user["id"]


def test_password_verify():
    udb.create_user("bob", "hunter2")
    u = udb.get_user_by_username("bob")
    assert udb.verify_password("hunter2", u["password_hash"])
    assert not udb.verify_password("wrong", u["password_hash"])


def test_list_users():
    udb.create_user("u1", "pw1")
    udb.create_user("u2", "pw2")
    users = udb.list_users()
    assert len(users) == 2


def test_update_user_role_and_active():
    user = udb.create_user("carol", "pw")
    updated = udb.update_user(user["id"], role="demo", is_active=False)
    assert updated["role"] == "demo"
    assert updated["is_active"] == 0


def test_update_question_limit_to_null():
    user = udb.create_user("dave", "pw", question_limit=10)
    assert user["question_limit"] == 10
    updated = udb.update_user(user["id"], question_limit=None)
    assert updated["question_limit"] is None


def test_delete_user():
    user = udb.create_user("eve", "pw")
    assert udb.delete_user(user["id"])
    assert udb.get_user_by_id(user["id"]) is None


def test_question_limit_enforcement():
    user = udb.create_user("frank", "pw", question_limit=2)
    assert udb.try_increment_if_under_limit(user["id"])  # 1
    assert udb.try_increment_if_under_limit(user["id"])  # 2
    assert not udb.try_increment_if_under_limit(user["id"])  # blocked at limit


def test_unlimited_user_always_allowed():
    user = udb.create_user("grace", "pw", question_limit=None)
    for _ in range(20):
        assert udb.try_increment_if_under_limit(user["id"])


def test_log_usage_and_cost():
    user = udb.create_user("henry", "pw")
    udb.log_usage(user["id"], "sess1", "what is X?", "haiku", 1000, 500)
    logs = udb.get_user_usage(user["id"])
    assert len(logs) == 1
    log = logs[0]
    assert log["prompt_tokens"] == 1000
    assert log["completion_tokens"] == 500
    # haiku: 1000/1000 * 0.00025 + 500/1000 * 0.00125 = 0.00025 + 0.000625 = 0.000875
    assert abs(log["total_cost_usd"] - 0.000875) < 1e-9


def test_total_cost_aggregation():
    user = udb.create_user("irene", "pw")
    udb.log_usage(user["id"], "s1", "q1", "haiku", 1000, 0)   # 0.00025
    udb.log_usage(user["id"], "s2", "q2", "sonnet", 1000, 0)  # 0.003
    total = udb.get_user_total_cost(user["id"])
    assert abs(total - 0.00325) < 1e-9


def test_seed_defaults_runs_once():
    udb.seed_defaults("siteuser", "sitepass")
    users = udb.list_users()
    usernames = {u["username"] for u in users}
    assert "demo" in usernames
    assert "siteuser" in usernames
    assert len(users) == 2

    # Second call should be a no-op
    udb.seed_defaults("siteuser", "sitepass")
    assert len(udb.list_users()) == 2


# ── FastAPI route tests ───────────────────────────────────────────────────────

from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from jose import jwt as _jwt

# Build a minimal test app that only mounts the routes we need
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def _make_test_app():
    from backend.api.routes.admin import router as admin_router
    from backend.api.routes.auth import router as auth_router
    app = FastAPI()
    app.include_router(auth_router, prefix="/api")
    app.include_router(admin_router, prefix="/api")
    return app


def _admin_token() -> str:
    from backend.api.deps import _secret, _ALGORITHM
    exp = datetime.now(tz=timezone.utc) + timedelta(hours=1)
    return _jwt.encode({"sub": "admin", "exp": exp}, _secret(), algorithm=_ALGORITHM)


@pytest.fixture()
def client():
    app = _make_test_app()
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def admin_headers():
    return {"Authorization": f"Bearer {_admin_token()}"}


def test_create_user_api(client, admin_headers):
    resp = client.post(
        "/api/admin/users",
        json={"username": "testuser", "password": "pw123", "role": "user"},
        headers=admin_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "testuser"
    assert "password_hash" not in data


def test_create_duplicate_user_returns_409(client, admin_headers):
    client.post(
        "/api/admin/users",
        json={"username": "dup", "password": "pw", "role": "user"},
        headers=admin_headers,
    )
    resp = client.post(
        "/api/admin/users",
        json={"username": "dup", "password": "pw", "role": "user"},
        headers=admin_headers,
    )
    assert resp.status_code == 409


def test_list_users_api(client, admin_headers):
    client.post("/api/admin/users", json={"username": "a", "password": "p", "role": "user"}, headers=admin_headers)
    client.post("/api/admin/users", json={"username": "b", "password": "p", "role": "demo"}, headers=admin_headers)
    resp = client.get("/api/admin/users", headers=admin_headers)
    assert resp.status_code == 200
    users = resp.json()
    assert len(users) == 2


def test_patch_user_disable(client, admin_headers):
    create_resp = client.post(
        "/api/admin/users",
        json={"username": "patched", "password": "pw", "role": "user"},
        headers=admin_headers,
    )
    user_id = create_resp.json()["id"]

    resp = client.patch(
        f"/api/admin/users/{user_id}",
        json={"is_active": False},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] == 0


def test_delete_user_api(client, admin_headers):
    create_resp = client.post(
        "/api/admin/users",
        json={"username": "todelete", "password": "pw", "role": "user"},
        headers=admin_headers,
    )
    user_id = create_resp.json()["id"]
    resp = client.delete(f"/api/admin/users/{user_id}", headers=admin_headers)
    assert resp.status_code == 204

    list_resp = client.get("/api/admin/users", headers=admin_headers)
    ids = [u["id"] for u in list_resp.json()]
    assert user_id not in ids


def test_admin_routes_require_auth(client):
    assert client.get("/api/admin/users").status_code == 401
    assert client.post("/api/admin/users", json={}).status_code == 401


def test_login_valid(client):
    udb.create_user("loginuser", "pass123", role="user")
    resp = client.post("/api/auth/login", json={"username": "loginuser", "password": "pass123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "token" in data
    assert data["role"] == "user"


def test_login_wrong_password(client):
    udb.create_user("loginuser2", "correct")
    resp = client.post("/api/auth/login", json={"username": "loginuser2", "password": "wrong"})
    assert resp.status_code == 401


def test_login_disabled_account(client):
    udb.create_user("disabled", "pw", is_active=False)
    resp = client.post("/api/auth/login", json={"username": "disabled", "password": "pw"})
    assert resp.status_code == 403
    assert "disabled" in resp.json()["detail"].lower()


def test_login_returns_demo_status_for_limited_user(client):
    udb.create_user("limited", "pw", role="user", question_limit=3)
    resp = client.post("/api/auth/login", json={"username": "limited", "password": "pw"})
    assert resp.status_code == 200
    data = resp.json()
    assert "demo" in data
    assert data["demo"]["questions_limit"] == 3
