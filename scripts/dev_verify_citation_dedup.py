"""
Throwaway dev script — NOT a permanent test.

The sample interview session produced by dev_generate_sample_report.py happened
to synthesize one "topic to study" per question (the model correctly kept
same-tagged-but-substantively-different questions separate), so that run alone
doesn't exercise the multi-question union/dedup/tie-break branch of
InterviewerPipeline._citation_from_contributing_questions.

This script exercises that branch directly, using the REAL per-question
citations already produced by real grading in scripts/sample_session_report.json
(no fabricated scores/citations) — it just calls the real deterministic
aggregation function with a synthetic multi-index topic to prove dedup-by-URL
and highest-score tie-break work against real retrieval data.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from backend.core.interviewer_pipeline import InterviewerPipeline

report = json.loads((_ROOT / "scripts" / "sample_session_report.json").read_text())["report"]
per_question = report["per_question"]

for q in per_question:
    urls = [c["url"] for c in (q.get("citations") or [])]
    print(f"Q{q['question_index']} citations ({len(urls)}): {urls[:2]}{'...' if len(urls) > 2 else ''}")

print("\n--- Union of Q6 + Q7 (both real, both cite the AEP identity glossary page) ---")
link = InterviewerPipeline._citation_from_contributing_questions([6, 7], per_question)
print("Grounded link:", link)
q6_citations = {c["url"]: c["score"] for c in per_question[5]["citations"]}
q7_citations = {c["url"]: c["score"] for c in per_question[6]["citations"]}
all_scores = {**q6_citations, **{k: max(v, q6_citations.get(k, -1)) for k, v in q7_citations.items()}}
expected_url = max(all_scores, key=all_scores.get)
assert link is not None and link["url"] == expected_url, (
    f"expected top-scored union citation {expected_url!r}, got {link}"
)
print(f"[OK] picked the highest-scored citation across both questions' real citation sets: {expected_url}")

print("\n--- Union of all 8 questions (broadest dedup case) ---")
link_all = InterviewerPipeline._citation_from_contributing_questions(list(range(1, 9)), per_question)
print("Grounded link:", link_all)

print("\n--- No matching source_question_indices -> None (falls back to fresh retrieval upstream) ---")
link_none = InterviewerPipeline._citation_from_contributing_questions([99], per_question)
assert link_none is None
print("[OK] returns None when no contributing question matches, as expected.")
