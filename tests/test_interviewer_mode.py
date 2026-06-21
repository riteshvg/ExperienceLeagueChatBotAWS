"""Tests for Interviewer Mode configuration and session logic."""

from __future__ import annotations

import json

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
    assert get_session(session.session_id) is session


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
    for q in session.questions:
        session.draft_answers[q.id] = f"Answer about {q.topic}"
    session.phase = "review"
    session.awaiting_advance = False

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
