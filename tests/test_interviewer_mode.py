"""Tests for Interviewer Mode configuration and session logic."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from backend.core.interviewer_pipeline import (
    InterviewerPipeline,
    create_session,
    get_session,
    _parse_evaluation_json,
)
from config.interview_profiles import (
    get_profiles_payload,
    get_question_set,
    validate_profile,
)


def _fake_message(text: str):
    return SimpleNamespace(content=[SimpleNamespace(text=text)])


def test_profiles_payload_structure():
    payload = get_profiles_payload()
    assert len(payload["levels"]) == 4
    assert len(payload["solutions"]) == 5
    assert len(payload["collections"]) == 4
    assert len(payload["combinations"]) >= 14
    ids = {l["id"] for l in payload["levels"]}
    assert ids == {"junior", "senior", "architect", "principal"}
    solution_ids = {s["id"] for s in payload["solutions"]}
    assert "all" in solution_ids


def test_validate_profile_success():
    assert validate_profile("senior", "cja") is None
    assert validate_profile("senior", "all") is None
    assert validate_profile("principal", "data_foundation") is None
    assert validate_profile("principal", "all") is None


def test_validate_profile_errors():
    assert "Unknown level" in validate_profile("staff", "cja")
    assert "Unknown solution" in validate_profile("senior", "invalid")
    assert "Unknown collection" in validate_profile("principal", "cja")


def test_question_set_sizes():
    cja_senior = get_question_set("senior", "cja")
    assert len(cja_senior) >= 5
    assert all(q.question and q.topic for q in cja_senior)

    principal = get_question_set("principal", "cross_solution_architecture")
    assert len(principal) >= 5

    all_senior = get_question_set("senior", "all")
    assert len(all_senior) >= 6
    assert len({q.id for q in all_senior}) == len(all_senior)


def test_session_save_and_advance():
    session = create_session("user-1", "junior", "cja")
    assert session.phase == "questioning"
    q1 = session.current_question()
    assert q1 is not None

    with pytest.raises(ValueError, match="Save an answer"):
        session.advance()

    saved = session.save_current_answer("CJA is person-centric analytics.")
    assert saved["question_id"] == q1.id
    assert session.awaiting_advance is True

    result = session.advance()
    assert session.phase == "questioning"
    assert result["current_question"] is not None

    # get_session rebuilds from Postgres (no in-process cache), so this is a
    # different object than `session` — assert the persisted state matches instead.
    reloaded = get_session(session.session_id)
    assert reloaded is not None
    assert reloaded.session_id == session.session_id
    assert reloaded.phase == session.phase
    assert reloaded.current_index == session.current_index
    assert reloaded.draft_answers[q1.id] == "CJA is person-centric analytics."


def test_session_enters_review_after_last_question():
    session = create_session("user-2", "junior", "cja")
    while session.phase == "questioning":
        q = session.current_question()
        assert q is not None
        session.save_current_answer(f"Answer for {q.id}")
        session.advance()
    assert session.phase == "review"
    assert session.all_answered()
    assert len(session.get_review_items()) == session.total


def test_parse_evaluation_json_fallback():
    raw = json.dumps({
        "score": 4,
        "score_pct": 80,
        "strengths": ["Good XDM explanation"],
        "gaps": ["Missing identity detail"],
        "model_answer_outline": "- Schema\n- Identity",
        "feedback": "Solid answer.",
    })
    data = _parse_evaluation_json(raw)
    assert data["score"] == 4
    assert data["strengths"][0] == "Good XDM explanation"


@pytest.mark.asyncio
async def test_stream_submit_without_llm():
    session = create_session("user-3", "junior", "cja")
    while session.phase == "questioning":
        q = session.current_question()
        session.save_current_answer(f"Answer about {q.topic}")
        session.advance()
    assert session.phase == "review"

    pipeline = InterviewerPipeline(retriever=None)
    events = []
    async for event in pipeline.stream_submit(session):
        events.append(event)

    types = [e["type"] for e in events]
    assert "evaluating" in types
    assert "session_report" in types
    assert "done" in types
    assert session.phase == "complete"
    assert session.evaluated is True
    report = next(e for e in events if e["type"] == "session_report")
    assert report["overall_score"] >= 1
    assert len(report["per_question"]) == session.total


@pytest.mark.asyncio
async def test_stream_start_yields_question():
    session = create_session("user-4", "senior", "target")
    pipeline = InterviewerPipeline(retriever=None)
    events = []
    async for event in pipeline.stream_start(session):
        events.append(event)

    assert any(e["type"] == "question" for e in events)
    assert any(e["type"] == "done" for e in events)


# ── Adaptive follow-ups (Phase 1) ────────────────────────────────────────────

def test_maybe_generate_followup_fails_open_without_client():
    session = create_session("followup-user-noclient", "junior", "cja")
    q = session.current_question()
    pipeline = InterviewerPipeline(retriever=None)
    pipeline._client = None  # simulate no ANTHROPIC_API_KEY configured

    import asyncio
    result = asyncio.run(pipeline.maybe_generate_followup(session, q, "a thin answer"))
    assert result is None


@pytest.mark.asyncio
async def test_maybe_generate_followup_ok_answer_returns_none():
    session = create_session("followup-user-ok", "junior", "cja")
    q = session.current_question()
    pipeline = InterviewerPipeline(retriever=None)
    pipeline._client = SimpleNamespace(
        messages=SimpleNamespace(create=AsyncMock(return_value=_fake_message("OK")))
    )

    result = await pipeline.maybe_generate_followup(session, q, "a solid, complete answer")
    assert result is None
    from backend.core import google_db
    assert google_db.get_followup_for_parent(session.session_id, q.id) is None


@pytest.mark.asyncio
async def test_maybe_generate_followup_weak_answer_generates_and_persists():
    session = create_session("followup-user-weak", "junior", "cja")
    q = session.current_question()
    pipeline = InterviewerPipeline(retriever=None)
    pipeline._client = SimpleNamespace(
        messages=SimpleNamespace(create=AsyncMock(side_effect=[
            _fake_message("WEAK"),
            _fake_message("Can you say more about person-centric reporting specifically?"),
        ]))
    )

    result = await pipeline.maybe_generate_followup(session, q, "it's a tool")
    assert result is not None
    assert result["question_id"] == f"{q.id}-fu"
    assert result["question"] == "Can you say more about person-centric reporting specifically?"
    assert result["parent_question_id"] == q.id

    from backend.core import google_db
    persisted = google_db.get_followup_for_parent(session.session_id, q.id)
    assert persisted is not None
    assert persisted["followup_prompt_text"] == result["question"]


@pytest.mark.asyncio
async def test_maybe_generate_followup_retry_skips_regeneration():
    session = create_session("followup-user-retry", "junior", "cja")
    q = session.current_question()
    pipeline = InterviewerPipeline(retriever=None)
    mock_create = AsyncMock(side_effect=[
        _fake_message("WEAK"),
        _fake_message("First generated follow-up text"),
    ])
    pipeline._client = SimpleNamespace(messages=SimpleNamespace(create=mock_create))

    first = await pipeline.maybe_generate_followup(session, q, "thin answer")
    assert first is not None
    assert mock_create.call_count == 2

    # Retry (e.g. a duplicate /answer POST) must not call the LLM again, and
    # must return the exact same persisted follow-up.
    second = await pipeline.maybe_generate_followup(session, q, "thin answer (resubmitted)")
    assert second == first
    assert mock_create.call_count == 2  # unchanged — short-circuited before any LLM call


def test_insert_followup_updates_session_total_and_order():
    session = create_session("followup-user-splice", "junior", "cja")
    q = session.current_question()
    original_total = session.total

    from config.interview_profiles import InterviewQuestion
    followup = InterviewQuestion(
        id=f"{q.id}-fu",
        question="Follow-up question text",
        topic=q.topic,
        difficulty=q.difficulty,
        expected_themes=q.expected_themes,
        retrieval_hint=q.retrieval_hint,
        version=q.version,
        is_followup=True,
    )
    session.insert_followup(followup)

    assert session.total == original_total + 1
    assert session.questions[session.current_index + 1].id == followup.id
    assert session.questions[session.current_index + 1].is_followup is True


@pytest.mark.asyncio
async def test_maybe_generate_followup_never_chains_on_a_followup_itself():
    """A weak answer to a follow-up must never spawn a second, chained follow-up."""
    session = create_session("followup-user-nochain", "junior", "cja")
    q = session.current_question()

    from config.interview_profiles import InterviewQuestion
    followup_question = InterviewQuestion(
        id=f"{q.id}-fu",
        question="Generated follow-up",
        topic=q.topic,
        difficulty=q.difficulty,
        expected_themes=q.expected_themes,
        retrieval_hint=q.retrieval_hint,
        version=q.version,
        is_followup=True,
    )

    pipeline = InterviewerPipeline(retriever=None)
    mock_create = AsyncMock(side_effect=[
        _fake_message("WEAK"),
        _fake_message("This should never be generated"),
    ])
    pipeline._client = SimpleNamespace(messages=SimpleNamespace(create=mock_create))

    result = await pipeline.maybe_generate_followup(session, followup_question, "a thin answer to the follow-up")

    assert result is None
    assert mock_create.call_count == 0  # never even attempted detection

    from backend.core import google_db
    assert google_db.get_followup_for_parent(session.session_id, followup_question.id) is None
