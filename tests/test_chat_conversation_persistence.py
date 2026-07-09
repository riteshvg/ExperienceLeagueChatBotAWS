"""Chat streaming endpoint — conversation persistence hook in event_generator().

Verifies: (1) a turn gets persisted with the right roles/citations/evidence/turn info,
(2) an existing conversation_id is reused rather than creating a new one,
(3) persistence failures never break the SSE response to the client (non-fatal by design),
(4) clarification-only responses are skipped (matches the existing usage-tracking skip).
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.api.deps import get_pipeline, get_session_store, get_site_user
from backend.api.routes.chat import router as chat_router


class FakePipeline:
    def __init__(self, events):
        self._events = events

    async def stream(self, **kwargs):
        for event in self._events:
            yield event


class FakeSessionStore:
    def new_session(self):
        return "fake-session-id"


def _events(model="sonnet"):
    return [
        {"type": "token", "content": "Hello "},
        {"type": "token", "content": "world"},
        {"type": "citations", "citations": [{"url": "https://experienceleague.adobe.com/x", "title": "Doc"}]},
        {"type": "evidence", "source_count": 1, "citation_count": 1, "top_score": 0.9, "avg_score": 0.9,
         "evidence_level": "strong", "grounding_level": "documented", "match_label": "Strong match",
         "grounding_label": "Documented", "sources": []},
        {"type": "done", "model": model, "session_id": "fake-session-id", "input_tokens": 10, "output_tokens": 20},
    ]


def _make_app(events):
    app = FastAPI()
    app.include_router(chat_router, prefix="/api")
    app.dependency_overrides[get_pipeline] = lambda: FakePipeline(events)
    app.dependency_overrides[get_session_store] = lambda: FakeSessionStore()
    app.dependency_overrides[get_site_user] = lambda: {
        "sub": "user@example.com", "role": "user", "uid": "google-sub-123",
        "email": "user@example.com", "name": "Test User",
    }
    return app


def _parse_sse(text: str) -> list[dict]:
    events = []
    for line in text.splitlines():
        if line.startswith("data: "):
            events.append(json.loads(line[len("data: "):]))
    return events


def test_new_conversation_created_and_turn_persisted():
    app = _make_app(_events())
    with TestClient(app) as client, \
         patch("backend.core.google_db.create_conversation", return_value={"id": 42}) as mock_create, \
         patch("backend.core.google_db.append_message") as mock_append:
        resp = client.post("/api/chat", json={"query": "How do I create a segment?"})

    assert resp.status_code == 200
    mock_create.assert_called_once_with("google-sub-123", title="How do I create a segment?")

    assert mock_append.call_count == 2
    user_call, assistant_call = mock_append.call_args_list
    assert user_call.args == (42, "user", "How do I create a segment?")
    assert assistant_call.args[:3] == (42, "assistant", "Hello world")
    assert assistant_call.kwargs["citations"] == [{"url": "https://experienceleague.adobe.com/x", "title": "Doc"}]
    assert assistant_call.kwargs["evidence"]["evidence_level"] == "strong"
    assert assistant_call.kwargs["model"] == "sonnet"

    done_event = _parse_sse(resp.text)[-1]
    assert done_event["conversation_id"] == 42


def test_existing_conversation_id_is_reused_not_recreated():
    app = _make_app(_events())
    with TestClient(app) as client, \
         patch("backend.core.google_db.create_conversation") as mock_create, \
         patch("backend.core.google_db.append_message") as mock_append:
        resp = client.post("/api/chat", json={"query": "follow-up", "conversation_id": 99})

    assert resp.status_code == 200
    mock_create.assert_not_called()
    user_call, _ = mock_append.call_args_list
    assert user_call.args[0] == 99

    done_event = _parse_sse(resp.text)[-1]
    assert done_event["conversation_id"] == 99


def test_persistence_failure_does_not_break_chat_response():
    """The try/except around persistence must swallow DB errors — the user still gets their answer."""
    app = _make_app(_events())
    with TestClient(app) as client, \
         patch("backend.core.google_db.create_conversation", side_effect=RuntimeError("DB unreachable")):
        resp = client.post("/api/chat", json={"query": "How do I create a segment?"})

    assert resp.status_code == 200
    events = _parse_sse(resp.text)
    tokens = "".join(e["content"] for e in events if e["type"] == "token")
    assert tokens == "Hello world"
    done_event = events[-1]
    assert done_event["type"] == "done"
    assert done_event["model"] == "sonnet"
    # Persistence failed, so no conversation_id should be attached
    assert "conversation_id" not in done_event


def test_clarification_only_response_is_not_persisted():
    app = _make_app(_events(model="clarification"))
    with TestClient(app) as client, \
         patch("backend.core.google_db.create_conversation") as mock_create, \
         patch("backend.core.google_db.append_message") as mock_append:
        resp = client.post("/api/chat", json={"query": "ambiguous query"})

    assert resp.status_code == 200
    mock_create.assert_not_called()
    mock_append.assert_not_called()
