"""
Throwaway dev script — NOT a permanent test.

Drives the REAL Interviewer Mode pipeline end-to-end (real Postgres session,
real Chroma retrieval, real Anthropic grading + synthesis calls) to produce a
sample `session_report` for visual QA of the three debrief-synthesis fixes:
  1. overall_score is now a deterministic mean of per-question scores.
  2. "Topics to study" links are grounded in the citations that actually backed
     the grading of their contributing questions.
  3. The PDF (rendered separately by generateInterviewReportPdf.ts) embeds a
     Unicode font so arrows/punctuation don't garble.

This script deliberately does NOT hit the FastAPI routes — it calls the same
plain Python functions the routes call (create_session, session.save_current_answer,
session.advance, InterviewerPipeline.stream_submit) so it can run headless, but
every one of those calls is the real production code path: real DB writes,
real retrieval, real LLM calls. Nothing here is mocked or stubbed.

Usage:
    python scripts/dev_generate_sample_report.py

Requires .env with a working DATABASE_URL, ANTHROPIC_API_KEY, and AWS creds
for Bedrock embeddings (same as running the app locally).
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv
load_dotenv(_ROOT / ".env", override=False)

from backend.core.chroma_retriever import ChromaRetriever
from backend.core.interviewer_pipeline import InterviewerPipeline, create_session
from config.interview_profiles import profile_label

OUTPUT_PATH = _ROOT / "scripts" / "sample_session_report.json"

# One deliberately weak/thin answer, one strong, and the rest middling — and a
# couple of intentionally shallow "I know the UI but not the underlying model"
# answers on architecture-flavored questions to encourage the synthesis step
# to group them under a shared "topic to study" (exercises the citation
# dedup/tie-break logic in _citation_from_contributing_questions).
ANSWER_BANK = {
    "architecture": (
        "Honestly I mostly just use the UI to wire things up — I know you connect "
        "AEP to CJA and then activate somewhere, but I couldn't explain the "
        "underlying data model or why the connections are structured that way."
    ),
    "integration": (
        "I think you just create a connection in CJA pointing at the AEP dataset "
        "and it syncs automatically. Not sure what a data view actually does under "
        "the hood."
    ),
    "identity": (
        "Strong answer: identity resolution across Web SDK, AEP, and CJA relies on "
        "ECID as the primary device identifier which gets stitched to a person ID "
        "once known IDs (e.g. CRM ID, login ID) are captured via identity graph "
        "namespaces. You'd configure a merge policy that prioritizes authenticated "
        "namespaces over device IDs, and CJA's person-based stitching in the "
        "connection/data view reflects the same identity graph so cross-channel "
        "journeys resolve to one person rather than fragmenting by device. Privacy "
        "labels and consent propagate through the same profile so downstream "
        "destinations respect opt-outs."
    ),
    "default_weak": (
        "Not sure, I'd probably look this up in the docs when I hit it."
    ),
    "default": (
        "You'd typically approach this by defining clear ownership between the "
        "platform team and the business stakeholders, using the standard Adobe "
        "tooling for the relevant product, and validating with a pilot before "
        "wider rollout."
    ),
}


def answer_for(question) -> str:  # noqa: ANN001 - InterviewQuestion, avoid import cycle in annotation
    topic = question.topic
    if topic in ANSWER_BANK:
        return ANSWER_BANK[topic]
    if question.question_type == "scenario":
        return ANSWER_BANK["default"]
    if question.difficulty <= 2:
        return ANSWER_BANK["default_weak"]
    return ANSWER_BANK["default"]


async def main() -> None:
    print("Constructing real ChromaRetriever (real Bedrock Titan embeddings)...")
    retriever = ChromaRetriever()

    print("Creating a real interview session (level=principal, profile_id=all)...")
    session = create_session(user_id="dev-script-qa", level="principal", profile_id="all")
    print(f"  session_id={session.session_id}  questions={session.total}")
    for i, q in enumerate(session.questions, 1):
        print(f"  Q{i} [{q.question_type}] topic={q.topic!r}: {q.question[:80]}")

    for q in session.questions:
        answer = answer_for(q)
        result = session.save_current_answer(answer)
        print(f"Saved answer for Q{result['question_index']} ({len(answer)} chars)")
        session.advance()  # on the last question this flips phase -> "review"

    assert session.phase == "review", f"expected phase=review, got {session.phase}"

    pipeline = InterviewerPipeline(retriever)

    print("\nCalling the REAL stream_submit() — real per-question grading + real "
          "synthesis LLM calls follow. This is not stubbed.\n")
    session_report = None
    async for event in pipeline.stream_submit(session):
        etype = event.get("type")
        if etype == "question_evaluation":
            print(f"  graded Q{event['question_index']}: score={event['score']}/5 ({event['score_pct']}%)")
        elif etype == "error":
            print(f"  ERROR: {event['message']}")
        elif etype == "session_report":
            session_report = {k: v for k, v in event.items() if k != "type"}

    if session_report is None:
        print("No session_report produced — check the error output above.")
        return

    per_question_scores = [r["score"] for r in session_report["per_question"]]
    arithmetic_mean = round(sum(per_question_scores) / len(per_question_scores), 1)
    print("\n--- Sanity checks ---")
    print(f"per-question scores: {per_question_scores}")
    print(f"arithmetic mean:     {arithmetic_mean}")
    print(f"overall_score:       {session_report['overall_score']}")
    assert session_report["overall_score"] == arithmetic_mean, (
        "overall_score no longer matches the arithmetic mean of per-question scores — "
        "the deterministic-mean fix regressed."
    )
    print("overall_score matches the arithmetic mean. [OK]")

    print("\ntopics_to_read:")
    for t in session_report["topics_to_read"]:
        print(f"  - {t['topic']!r} -> {t.get('url', '(no link)')}")

    payload = {
        "report": session_report,
        "debriefText": session_report.get("overall_feedback", ""),
        "level": session.level,
        "profileLabel": profile_label(session.level, session.profile_id),
    }
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2))
    print(f"\nWrote {OUTPUT_PATH}")
    print("Next: cd frontend && npx tsx scripts/dev_render_sample_report_pdf.ts")


if __name__ == "__main__":
    asyncio.run(main())
