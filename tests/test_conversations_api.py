"""Conversation persistence API — auth scoping and CRUD behavior.

google_db's Postgres functions are mocked; these tests exercise the router's
logic (dependency wiring, ownership scoping via user_id, 404 handling), not
the SQL itself (no Postgres available in this test environment).
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.api.deps import get_site_user
from backend.api.routes.conversations import router as conversations_router


def _make_test_app():
    app = FastAPI()
    app.include_router(conversations_router, prefix="/api")
    app.dependency_overrides[get_site_user] = lambda: {
        "sub": "user@example.com",
        "role": "user",
        "uid": "google-sub-123",
        "email": "user@example.com",
        "name": "Test User",
    }
    return app


@pytest.fixture()
def client():
    app = _make_test_app()
    with TestClient(app) as c:
        yield c


def test_list_conversations_scoped_to_uid(client):
    with patch("backend.core.google_db.list_conversations") as mock_list:
        mock_list.return_value = [{"id": 1, "user_id": "google-sub-123", "title": "Segments"}]
        resp = client.get("/api/conversations")
    assert resp.status_code == 200
    assert resp.json() == {"conversations": [{"id": 1, "user_id": "google-sub-123", "title": "Segments"}]}
    mock_list.assert_called_once_with("google-sub-123")


def test_get_conversation_not_found_returns_404(client):
    with patch("backend.core.google_db.get_conversation", return_value=None) as mock_get:
        resp = client.get("/api/conversations/999")
    assert resp.status_code == 404
    mock_get.assert_called_once_with(999, "google-sub-123")


def test_get_conversation_success(client):
    detail = {"id": 5, "user_id": "google-sub-123", "title": "Segments", "messages": []}
    with patch("backend.core.google_db.get_conversation", return_value=detail):
        resp = client.get("/api/conversations/5")
    assert resp.status_code == 200
    assert resp.json() == detail


def test_get_conversation_owned_by_other_user_returns_404(client):
    """Ownership check happens inside google_db.get_conversation (scoped query) —
    the route must surface that as 404, never leak another user's conversation."""
    with patch("backend.core.google_db.get_conversation", return_value=None) as mock_get:
        resp = client.get("/api/conversations/42")
    assert resp.status_code == 404
    # Must pass the *authenticated* uid, not something from the request body/query
    mock_get.assert_called_once_with(42, "google-sub-123")


def test_rename_conversation_not_found_returns_404(client):
    with patch("backend.core.google_db.rename_conversation", return_value=None) as mock_rename:
        resp = client.patch("/api/conversations/7", json={"title": "New title"})
    assert resp.status_code == 404
    mock_rename.assert_called_once_with(7, "google-sub-123", "New title")


def test_rename_conversation_success(client):
    updated = {"id": 7, "user_id": "google-sub-123", "title": "New title"}
    with patch("backend.core.google_db.rename_conversation", return_value=updated):
        resp = client.patch("/api/conversations/7", json={"title": "New title"})
    assert resp.status_code == 200
    assert resp.json() == updated


def test_delete_conversation_not_found_returns_404(client):
    with patch("backend.core.google_db.delete_conversation", return_value=False) as mock_delete:
        resp = client.delete("/api/conversations/3")
    assert resp.status_code == 404
    mock_delete.assert_called_once_with(3, "google-sub-123")


def test_delete_conversation_success(client):
    with patch("backend.core.google_db.delete_conversation", return_value=True):
        resp = client.delete("/api/conversations/3")
    assert resp.status_code == 200
    assert resp.json() == {"deleted": True}


def test_requires_auth_dependency():
    """Without a dependency override, an unauthenticated request must not reach google_db at all."""
    app = FastAPI()
    app.include_router(conversations_router, prefix="/api")
    with TestClient(app) as client:
        resp = client.get("/api/conversations")
    assert resp.status_code == 401
