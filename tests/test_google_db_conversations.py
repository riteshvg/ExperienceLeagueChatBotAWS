"""Conversation persistence functions in google_db.py — SQL/logic correctness via a mocked connection.

No real Postgres available in this environment, so _connect() is monkeypatched to return a
MagicMock whose cursor() context manager and fetchone/fetchall are scripted per test.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.core import google_db


class FakeCursor:
    def __init__(self, fetchone_results=None, fetchall_results=None):
        self._fetchone_results = list(fetchone_results or [])
        self._fetchall_results = list(fetchall_results or [])
        self.executed = []

    def execute(self, query, params=None):
        self.executed.append((query.strip(), params))

    def fetchone(self):
        return self._fetchone_results.pop(0) if self._fetchone_results else None

    def fetchall(self):
        return self._fetchall_results.pop(0) if self._fetchall_results else []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class FakeConn:
    def __init__(self, cursor: FakeCursor):
        self._cursor = cursor
        self.committed = False
        self.closed = False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.committed = True

    def close(self):
        self.closed = True


@pytest.fixture()
def fake_connect(monkeypatch):
    """Returns a factory: fake_connect(cursor) -> patches google_db._connect to return that conn."""

    def _apply(cursor: FakeCursor) -> FakeConn:
        conn = FakeConn(cursor)
        monkeypatch.setattr(google_db, "_connect", lambda: conn)
        return conn

    return _apply


def test_create_conversation_inserts_and_commits(fake_connect):
    cursor = FakeCursor(fetchone_results=[{"id": 1, "user_id": "u1", "title": "Hi", "created_at": None, "updated_at": None}])
    conn = fake_connect(cursor)

    result = google_db.create_conversation("u1", "Hi")

    assert result["id"] == 1
    assert conn.committed is True
    assert conn.closed is True
    insert_query, params = cursor.executed[0]
    assert "INSERT INTO exl_conversations" in insert_query
    assert params == ("u1", "Hi")


def test_append_message_computes_turn_order_from_max(fake_connect):
    # First query returns the "next_order" row, second is the INSERT, third the UPDATE.
    cursor = FakeCursor(fetchone_results=[{"next_order": 3}])
    fake_connect(cursor)

    google_db.append_message(
        conversation_id=1,
        role="assistant",
        content="answer text",
        citations=[{"url": "https://x"}],
        evidence={"evidence_level": "strong"},
        model="sonnet",
    )

    select_query, select_params = cursor.executed[0]
    assert "COALESCE(MAX(turn_order), -1) + 1" in select_query
    assert select_params == (1,)

    insert_query, insert_params = cursor.executed[1]
    assert "INSERT INTO exl_conversation_messages" in insert_query
    conversation_id, role, content, citations_json, evidence_json, model, turn_order = insert_params
    assert conversation_id == 1
    assert role == "assistant"
    assert content == "answer text"
    assert json.loads(citations_json) == [{"url": "https://x"}]
    assert json.loads(evidence_json) == {"evidence_level": "strong"}
    assert model == "sonnet"
    assert turn_order == 3  # picked up from next_order, not hardcoded 0

    update_query, update_params = cursor.executed[2]
    assert "UPDATE exl_conversations SET updated_at = NOW()" in update_query
    assert update_params == (1,)


def test_append_message_first_turn_starts_at_zero(fake_connect):
    """No existing messages -> COALESCE(MAX(...), -1) + 1 => 0, not 1 or None."""
    cursor = FakeCursor(fetchone_results=[{"next_order": 0}])
    fake_connect(cursor)

    google_db.append_message(conversation_id=9, role="user", content="hello")

    _, insert_params = cursor.executed[1]
    assert insert_params[-1] == 0


def test_append_message_null_citations_evidence_not_json_dumped(fake_connect):
    """citations=None/evidence=None must stay SQL NULL, not the string 'null'."""
    cursor = FakeCursor(fetchone_results=[{"next_order": 0}])
    fake_connect(cursor)

    google_db.append_message(conversation_id=1, role="user", content="hi", citations=None, evidence=None)

    _, insert_params = cursor.executed[1]
    citations_json, evidence_json = insert_params[3], insert_params[4]
    assert citations_json is None
    assert evidence_json is None


def test_get_conversation_scopes_by_user_id(fake_connect):
    conv_row = {"id": 5, "user_id": "u1", "title": "T", "created_at": None, "updated_at": None}
    msg_rows = [{"id": 1, "conversation_id": 5, "role": "user", "content": "hi", "citations": None,
                 "evidence": None, "model": None, "turn_order": 0, "created_at": None}]
    cursor = FakeCursor(fetchone_results=[conv_row], fetchall_results=[msg_rows])
    fake_connect(cursor)

    result = google_db.get_conversation(5, "u1")

    assert result is not None
    assert result["id"] == 5
    assert len(result["messages"]) == 1
    conv_query, conv_params = cursor.executed[0]
    assert "WHERE id = %s AND user_id = %s" in conv_query
    assert conv_params == (5, "u1")


def test_get_conversation_returns_none_when_not_owned(fake_connect):
    cursor = FakeCursor(fetchone_results=[None])
    fake_connect(cursor)

    result = google_db.get_conversation(5, "someone-else")

    assert result is None
    # Must not attempt to fetch messages for a conversation it couldn't find/own
    assert len(cursor.executed) == 1


def test_delete_conversation_scoped_by_user_id(fake_connect):
    cursor = FakeCursor()
    cursor.rowcount = 1
    fake_connect(cursor)

    deleted = google_db.delete_conversation(5, "u1")

    assert deleted is True
    query, params = cursor.executed[0]
    assert "DELETE FROM exl_conversations WHERE id = %s AND user_id = %s" in query
    assert params == (5, "u1")


def test_delete_conversation_returns_false_when_not_found(fake_connect):
    cursor = FakeCursor()
    cursor.rowcount = 0
    fake_connect(cursor)

    assert google_db.delete_conversation(999, "u1") is False


def test_list_conversations_scoped_by_user_id(fake_connect):
    cursor = FakeCursor(fetchall_results=[[{"id": 1, "user_id": "u1", "title": "A", "created_at": None, "updated_at": None}]])
    fake_connect(cursor)

    result = google_db.list_conversations("u1")

    assert len(result) == 1
    query, params = cursor.executed[0]
    assert "WHERE user_id = %s" in query
    assert params == ("u1",)
