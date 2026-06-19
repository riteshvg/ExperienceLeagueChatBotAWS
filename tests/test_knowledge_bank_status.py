"""Tests for knowledge bank maintenance status."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from backend.core import knowledge_bank_status as kb


class _FakeRetriever:
    def __init__(self, count: int):
        self._count = count

    def document_count(self) -> int:
        return self._count


def _app(*, retriever=None, started_at=None):
    app = SimpleNamespace()
    app.state = SimpleNamespace(
        retriever=retriever,
        maintenance_started_at=started_at,
    )
    return app


def test_health_ok_when_chroma_populated(monkeypatch):
    monkeypatch.delenv("KNOWLEDGE_BANK_UPDATING", raising=False)
    app = _app(retriever=_FakeRetriever(100))
    payload = kb.build_health_payload(app)
    assert payload["status"] == "ok"
    assert payload["chromadb"]["document_count"] == 100
    assert "maintenance" not in payload


def test_health_updating_when_empty_chroma(monkeypatch):
    monkeypatch.delenv("KNOWLEDGE_BANK_UPDATING", raising=False)
    started = datetime(2026, 6, 19, 10, 0, tzinfo=timezone.utc)
    app = _app(retriever=_FakeRetriever(0), started_at=started)
    payload = kb.build_health_payload(app)
    assert payload["status"] == "updating"
    assert payload["maintenance"]["active"] is True
    assert "knowledge bank is being updated" in payload["maintenance"]["message"].lower()
    check_back = datetime.fromisoformat(payload["maintenance"]["check_back_at"])
    assert check_back == started + timedelta(minutes=4)


def test_manual_flag_forces_updating(monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_BANK_UPDATING", "true")
    monkeypatch.setenv(
        "KNOWLEDGE_BANK_UPDATE_STARTED_AT", "2026-06-19T09:30:00Z"
    )
    app = _app(retriever=_FakeRetriever(33000))
    assert kb.is_knowledge_bank_updating(app) is True
    payload = kb.build_health_payload(app)
    assert payload["status"] == "updating"


def test_maintenance_payload_detail_code():
    app = _app(retriever=None)
    payload = kb.build_maintenance_payload(app)
    assert payload["detail"] == "KNOWLEDGE_BANK_UPDATING"
    assert payload["maintenance"]["eta_minutes"] == 4
