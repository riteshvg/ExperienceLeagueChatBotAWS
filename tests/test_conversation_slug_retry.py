"""append_conversation_message's slug-collision retry.

idx_messages_slug is a partial UNIQUE index (WHERE slug IS NOT NULL) — by design,
only one published FAQ page per unique question (make_slug hashes the question
text). A repeated popular question must still persist as a message; it just loses
the slug/publish claim to whichever message got there first. Reproduced against
production: a duplicate-key error on this index was silently swallowed by chat.py's
outer try/except, so conversation_id never made it into the response.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from psycopg2.errors import UniqueViolation

_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.core import google_db


class FakeCursor:
    def __init__(self, fail_first=False):
        self.fail_first = fail_first
        self.executed = []

    def execute(self, query, params=None):
        self.executed.append((query.strip(), params))
        if self.fail_first:
            self.fail_first = False
            raise UniqueViolation('duplicate key value violates unique constraint "idx_messages_slug"')

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class FakeConn:
    def __init__(self, cursors):
        self._cursors = list(cursors)
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def cursor(self):
        return self._cursors.pop(0)

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


@pytest.fixture()
def fake_connect(monkeypatch):
    def _apply(conn: FakeConn) -> FakeConn:
        monkeypatch.setattr(google_db, "_connect", lambda: conn)
        return conn

    return _apply


def test_normal_insert_succeeds_without_retry(fake_connect):
    cursor = FakeCursor(fail_first=False)
    conn = fake_connect(FakeConn([cursor]))

    google_db.append_conversation_message(
        conversation_id="c1", role="assistant", content="answer",
        slug="how-do-i-create-a-segment-abc123", is_published=True,
    )

    assert len(cursor.executed) == 1
    assert conn.committed is True
    assert conn.rolled_back is False


def test_slug_collision_retries_without_slug(fake_connect):
    first_cursor = FakeCursor(fail_first=True)
    retry_cursor = FakeCursor(fail_first=False)
    conn = fake_connect(FakeConn([first_cursor, retry_cursor]))

    google_db.append_conversation_message(
        conversation_id="c1", role="assistant", content="answer",
        slug="how-do-i-create-a-segment-abc123", is_published=True,
    )

    assert conn.rolled_back is True
    assert conn.committed is True
    # Retry must drop the slug/publish claim, not just retry the same insert
    _, retry_params = retry_cursor.executed[0]
    retry_slug, retry_published = retry_params[5], retry_params[6]
    assert retry_slug is None
    assert retry_published is False


def test_collision_without_a_slug_is_not_swallowed(fake_connect):
    """A UniqueViolation on a message with no slug (e.g. the id PK) is a different,
    unexpected bug — must propagate, not be silently retried into a no-op."""
    cursor = FakeCursor(fail_first=True)
    fake_connect(FakeConn([cursor]))

    with pytest.raises(UniqueViolation):
        google_db.append_conversation_message(
            conversation_id="c1", role="user", content="hello", slug=None,
        )
