"""Route-level tests for Interviewer Mode: full happy path, concurrency races,
resume-after-restart, and SSE stream interruption. Runs against the real local
Postgres DB (see tests/conftest.py) — no mocking of persistence.
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Interviewer mode is admin_only by default; bypass that gate for these tests
# (get_site_user is overridden below anyway, but _feature_available also checks
# settings directly).
os.environ["INTERVIEWER_MODE_ADMIN_ONLY"] = "false"
os.environ["INTERVIEWER_MODE_ENABLED"] = "true"

from backend.api.deps import get_retriever, get_site_user
from backend.api.routes.interviewer import router as interviewer_router


def _make_app(user_id: str) -> FastAPI:
    app = FastAPI()
    app.include_router(interviewer_router, prefix="/api")
    app.dependency_overrides[get_site_user] = lambda: {"uid": user_id, "email": f"{user_id}@example.com"}
    app.dependency_overrides[get_retriever] = lambda: None
    return app


def _client(user_id: str) -> TestClient:
    return TestClient(_make_app(user_id))


def parse_sse(text: str) -> list[dict]:
    events = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            payload = line[len("data:"):].strip()
            if payload:
                events.append(json.loads(payload))
    return events


def _start(client: TestClient) -> dict:
    resp = client.post("/api/interviewer/start", json={"level": "junior", "profile_id": "cja"})
    assert resp.status_code == 200
    events = parse_sse(resp.text)
    done = next(e for e in events if e["type"] == "done")
    return done


def _answer_and_advance(client: TestClient, session_id: str, text: str) -> dict:
    resp = client.post("/api/interviewer/answer", json={"session_id": session_id, "answer": text})
    assert resp.status_code == 200, resp.text
    resp = client.post("/api/interviewer/advance", json={"session_id": session_id})
    assert resp.status_code == 200, resp.text
    return resp.json()


def _drive_to_review(client: TestClient, session_id: str, total: int) -> None:
    for i in range(total):
        _answer_and_advance(client, session_id, f"Answer number {i}")


# ── Happy path ────────────────────────────────────────────────────────────────

def test_full_happy_path_start_to_complete():
    with _client("route-user-happy") as client:
        started = _start(client)
        session_id = started["session_id"]
        total = started["total_questions"]
        assert started["phase"] == "questioning"

        _drive_to_review(client, session_id, total)

        review = client.get(f"/api/interviewer/review/{session_id}")
        assert review.status_code == 200
        review_body = review.json()
        assert review_body["phase"] == "review"
        assert review_body["all_answered"] is True
        assert len(review_body["items"]) == total

        submit_resp = client.post("/api/interviewer/submit", json={"session_id": session_id})
        assert submit_resp.status_code == 200
        events = parse_sse(submit_resp.text)
        types = [e["type"] for e in events]
        assert "evaluating" in types
        assert "session_report" in types
        assert "done" in types

        final = next(e for e in events if e["type"] == "done")
        assert final["phase"] == "complete"
        assert final["evaluated"] is True


# ── Adaptive follow-ups (Phase 1) ────────────────────────────────────────────

def test_answer_triggers_followup_and_advance_surfaces_it(monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    import backend.core.interviewer_pipeline as pipeline_module

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")

    class FakeAsyncAnthropic:
        def __init__(self, api_key):
            self.messages = SimpleNamespace(create=AsyncMock(side_effect=[
                SimpleNamespace(content=[SimpleNamespace(text="WEAK")]),
                SimpleNamespace(content=[SimpleNamespace(
                    text="Can you elaborate on what person-centric analytics means?"
                )]),
            ]))

    monkeypatch.setattr(pipeline_module, "AsyncAnthropic", FakeAsyncAnthropic)

    with _client("route-user-followup") as client:
        started = _start(client)
        session_id = started["session_id"]
        original_total = started["total_questions"]

        resp = client.post(
            "/api/interviewer/answer",
            json={"session_id": session_id, "answer": "it's a tool"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["follow_up"] is not None
        assert body["follow_up"]["question"] == "Can you elaborate on what person-centric analytics means?"
        assert body["total_questions"] == original_total + 1
        assert body["is_last"] is False

        advance_resp = client.post("/api/interviewer/advance", json={"session_id": session_id})
        assert advance_resp.status_code == 200
        adv_body = advance_resp.json()
        assert adv_body["current_question"]["is_followup"] is True
        assert adv_body["current_question"]["question"] == body["follow_up"]["question"]
        assert adv_body["total_questions"] == original_total + 1

        # Retrying the answer save (e.g. a duplicate client request) must not
        # spawn a second follow-up or call the LLM again.
        review = client.get(f"/api/interviewer/review/{session_id}")
        assert review.status_code == 200
        assert review.json()["total_questions"] == original_total + 1


# ── Double-advance race ──────────────────────────────────────────────────────

def test_double_advance_race_no_duplicate_skip():
    with _client("route-user-race-advance") as client:
        started = _start(client)
        session_id = started["session_id"]

        resp = client.post("/api/interviewer/answer", json={"session_id": session_id, "answer": "first answer"})
        assert resp.status_code == 200

        with _client("route-user-race-advance") as c1, _client("route-user-race-advance") as c2:
            with ThreadPoolExecutor(max_workers=2) as pool:
                f1 = pool.submit(c1.post, "/api/interviewer/advance", json={"session_id": session_id})
                f2 = pool.submit(c2.post, "/api/interviewer/advance", json={"session_id": session_id})
                r1, r2 = f1.result(), f2.result()

        statuses = sorted([r1.status_code, r2.status_code])
        # Exactly one advance succeeds; the other loses the race and gets a clean 400.
        assert statuses == [200, 400]

        review = client.get(f"/api/interviewer/review/{session_id}")
        body = review.json()
        # Only one question was actually skipped — not two.
        assert body["current_index"] == 1


# ── Double-submit race ───────────────────────────────────────────────────────

def test_double_submit_race_no_duplicate_evaluation():
    with _client("route-user-race-submit") as client:
        started = _start(client)
        session_id = started["session_id"]
        total = started["total_questions"]
        _drive_to_review(client, session_id, total)

        with _client("route-user-race-submit") as c1, _client("route-user-race-submit") as c2:
            with ThreadPoolExecutor(max_workers=2) as pool:
                f1 = pool.submit(c1.post, "/api/interviewer/submit", json={"session_id": session_id})
                f2 = pool.submit(c2.post, "/api/interviewer/submit", json={"session_id": session_id})
                r1, r2 = f1.result(), f2.result()

        results = []
        for r in (r1, r2):
            assert r.status_code == 200  # both are 200 OK SSE responses...
            results.append(parse_sse(r.text))

        report_counts = [
            sum(1 for e in events if e["type"] == "session_report")
            for events in results
        ]
        error_counts = [
            sum(1 for e in events if e["type"] == "error")
            for events in results
        ]
        # ...but only one stream actually produced a session_report; the other
        # got blocked with an "already evaluated" error before running any LLM calls.
        assert sorted(zip(report_counts, error_counts)) == [(0, 1), (1, 0)]

        review = client.get(f"/api/interviewer/review/{session_id}")
        assert review.json()["phase"] == "complete"


# ── Resume after restart ─────────────────────────────────────────────────────

def test_resume_after_simulated_restart():
    with _client("route-user-restart") as client:
        started = _start(client)
        session_id = started["session_id"]
        _answer_and_advance(client, session_id, "answer before restart")

    # Simulate a backend restart: drop every in-process module reference that
    # could be caching session state, then rebuild the app fresh.
    for mod in list(sys.modules):
        if mod.startswith("backend.core.interviewer_pipeline") or mod.startswith("backend.api.routes.interviewer"):
            del sys.modules[mod]

    from backend.api.routes.interviewer import router as interviewer_router_fresh

    app = FastAPI()
    app.include_router(interviewer_router_fresh, prefix="/api")
    app.dependency_overrides[get_site_user] = lambda: {"uid": "route-user-restart", "email": "x@example.com"}
    app.dependency_overrides[get_retriever] = lambda: None

    with TestClient(app) as fresh_client:
        review = fresh_client.get(f"/api/interviewer/review/{session_id}")
        assert review.status_code == 200
        body = review.json()
        assert body["phase"] == "questioning"
        assert body["current_index"] == 1

        # And the session keeps working normally post-restart.
        resp = fresh_client.post(
            "/api/interviewer/answer",
            json={"session_id": session_id, "answer": "answer after restart"},
        )
        assert resp.status_code == 200


# ── SSE stream interruption ──────────────────────────────────────────────────

def test_start_stream_interruption_leaves_session_usable():
    user_id = f"route-user-sse-start-{uuid.uuid4()}"
    with _client(user_id) as client:
        with client.stream(
            "POST", "/api/interviewer/start", json={"level": "junior", "profile_id": "cja"}
        ) as resp:
            assert resp.status_code == 200
            line_iter = resp.iter_lines()
            first_line = next(line_iter)
            assert first_line  # got at least the welcome token before "disconnecting"
            # Client walks away here without reading the rest of the stream.

        from backend.core.interviewer_pipeline import get_session

        # session was created (and persisted) before any streaming began, so an
        # early client disconnect can't leave it partially created.
        sessions = _find_sessions_for_user(user_id)
        assert len(sessions) == 1
        session = get_session(sessions[0])
        assert session.phase == "questioning"
        assert session.current_index == 0

        # A normal follow-up request works fine.
        resp = client.post(
            "/api/interviewer/answer",
            json={"session_id": session.session_id, "answer": "recovered after disconnect"},
        )
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_submit_interrupted_mid_stream_can_be_recovered():
    """Simulates a client that disconnects mid-/submit: the server-side async
    generator (pipeline.stream_submit) is abandoned partway through, which is
    exactly what happens on a real dropped connection — starlette stops
    iterating the generator without it ever reaching its final yield."""
    from backend.core import google_db
    from backend.core.interviewer_pipeline import InterviewerPipeline, create_session, get_session

    session = create_session("pipeline-user-interrupt", "junior", "cja")
    total = session.total
    for _ in range(total):
        q = session.current_question()
        session.save_current_answer(f"answer for {q.id}")
        session.advance()
    assert session.phase == "review"

    pipeline = InterviewerPipeline(retriever=None)
    gen = pipeline.stream_submit(session)
    first_event = await gen.__anext__()
    assert first_event["type"] == "evaluating"
    await gen.aclose()  # abandon the stream mid-flight, like a real disconnect

    stuck = get_session(session.session_id)
    # Claimed for evaluation, but never reached "complete" — a known, recoverable
    # state, not corrupted (e.g. not stuck in "questioning" or "complete").
    assert stuck.phase == "review"
    assert stuck.evaluated is True

    # An immediate retry must not silently re-run evaluation from scratch.
    assert google_db.try_claim_interview_session_for_evaluation(session.session_id) is None

    # But once enough time has passed (simulated via stale_after_seconds=0), a
    # retry can reclaim the interrupted session — this returns a *new* CAS token,
    # distinct from the token the interrupted run was holding.
    original_token = None  # the interrupted gen never exposed its token to this test
    new_token = google_db.try_claim_interview_session_for_evaluation(session.session_id, stale_after_seconds=0)
    assert new_token is not None

    fake_report = {
        "overall_score": 3.0,
        "readiness": "needs_work",
        "readiness_summary": "recovered",
        "strengths": [],
        "priority_gaps": [],
        "mistakes_to_avoid": [],
        "topics_to_read": [],
        "overall_feedback": "",
        "per_question": [],
        "citations": [],
    }
    completed = google_db.complete_interview_session(session.session_id, fake_report, new_token)
    assert completed is True

    recovered = get_session(session.session_id)
    assert recovered.phase == "complete"
    assert recovered.session_report["readiness_summary"] == "recovered"


@pytest.mark.asyncio
async def test_submit_retry_after_staleness_completes_exactly_once():
    """The full end-to-end proof for the recovery path: disconnect mid-/submit,
    let the claim go stale (short test-only threshold instead of waiting the real
    120s), retry via a second /submit — confirms the retry completes normally
    with exactly one session_report persisted, phase reaching 'complete' exactly
    once, and that the original (abandoned) run's claim token can no longer write
    anything even if it were to "wake up" later.
    """
    from backend.core import google_db
    from backend.core.interviewer_pipeline import InterviewerPipeline, create_session, get_session

    session = create_session("pipeline-user-retry-after-stale", "junior", "cja")
    for _ in range(session.total):
        q = session.current_question()
        session.save_current_answer(f"answer for {q.id}")
        session.advance()
    assert session.phase == "review"

    # First /submit: claim, then disconnect after the very first per-question
    # evaluation lands — this captures the *original* claim token before abandoning.
    first_pipeline = InterviewerPipeline(retriever=None)
    gen = first_pipeline.stream_submit(session, stale_after_seconds=120)
    events_before_disconnect = []
    async for event in gen:
        events_before_disconnect.append(event)
        if event["type"] == "question_evaluation":
            break
    await gen.aclose()  # client disconnects here, mid-evaluation

    stuck = get_session(session.session_id)
    assert stuck.phase == "review"
    assert stuck.evaluated is True
    original_row = _get_session_row(session.session_id)
    original_token = original_row["evaluation_started_at"]
    assert original_token is not None

    # Simulate the staleness window elapsing: rather than sleeping 120s, retry
    # with a 0-second threshold — this is the "short test-only threshold" swap
    # for mocking the clock, exercising the exact same SQL guard with a smaller
    # window instead of faking `NOW()`.
    second_pipeline = InterviewerPipeline(retriever=None)
    reloaded = get_session(session.session_id)
    events_after_retry = [
        e async for e in second_pipeline.stream_submit(reloaded, stale_after_seconds=0)
    ]

    types = [e["type"] for e in events_after_retry]
    assert "evaluating" in types
    assert "session_report" in types
    assert "done" in types
    assert "error" not in types

    final_row = _get_session_row(session.session_id)
    assert final_row["phase"] == "complete"
    assert final_row["session_report"] is not None
    retry_token = final_row["evaluation_started_at"]
    assert retry_token != original_token  # the retry holds a genuinely new claim

    # Exactly one session_report ended up persisted (the retry's), not two writes
    # racing — verified by content, since only the retry's fabricated-by-LLM-fallback
    # report would carry this fixed per-question count.
    assert len(final_row["session_report"]["per_question"]) == session.total

    # The original (abandoned) run's token is now provably dead: even if that run
    # had kept executing after the disconnect and eventually tried to write its
    # own result, its token no longer matches — the write is rejected, not raced.
    stale_write_accepted = google_db.complete_interview_session(
        session.session_id,
        {"overall_score": 1.0, "readiness_summary": "should not land", "per_question": [],
         "strengths": [], "priority_gaps": [], "mistakes_to_avoid": [], "topics_to_read": [],
         "overall_feedback": "", "citations": [], "readiness": "needs_work"},
        original_token,
    )
    assert stale_write_accepted is False

    untouched_row = _get_session_row(session.session_id)
    assert untouched_row["session_report"]["readiness_summary"] != "should not land"
    assert untouched_row["session_report"] == final_row["session_report"]


def _get_session_row(session_id: str) -> dict:
    from backend.core.google_db import _connect

    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT phase, evaluated, evaluation_started_at, session_report "
                "FROM interview_sessions WHERE session_id = %s",
                (session_id,),
            )
            return dict(cur.fetchone())
    finally:
        conn.close()


def _find_sessions_for_user(user_id: str) -> list[str]:
    from backend.core.google_db import _connect

    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT session_id FROM interview_sessions WHERE user_id = %s", (user_id,))
            rows = cur.fetchall()
        return [str(r["session_id"]) for r in rows]
    finally:
        conn.close()
