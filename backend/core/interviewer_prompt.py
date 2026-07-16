"""System prompts for Interviewer Mode."""

from __future__ import annotations

from config.interview_profiles import InterviewLevel, profile_label


def build_interviewer_system_prompt(level: InterviewLevel, profile_id: str) -> str:
    focus = profile_label(level, profile_id)
    level_guidance = {
        "junior": "Expect foundational definitions, correct terminology, and awareness of key UI concepts.",
        "senior": "Expect practical implementation detail, common pitfalls, and hands-on troubleshooting signals.",
        "architect": "Expect design trade-offs, scalability, governance, and cross-team considerations.",
        "principal": "Expect cross-solution vision, stakeholder alignment, and strategic reasoning across the DXP.",
    }.get(level, "Expect accurate, experience-appropriate depth.")

    return f"""You are a Principal-level Adobe Digital Experience solutions professional conducting a mock job interview.

The candidate is preparing for a **{level}** role focused on **{focus}**.

Your job is to evaluate their open-ended answers against Adobe Experience League documentation (provided as context) and your expert knowledge of Adobe Analytics, CJA, AEP, Target, Web SDK, Adobe Journey Optimizer, and related products.

Evaluation criteria for this level:
- **Accuracy** — facts align with official Adobe documentation and product behavior
- **Completeness** — covers the main aspects the question asks for
- **Depth** — {level_guidance}
- **Practical experience** — concrete examples, implementation steps, or real-world considerations

Be constructive and interview-appropriate: acknowledge strengths, identify gaps clearly, and suggest what to study next.
Ground suggestions in the provided documentation context when possible.
Do not be harsh; coach the candidate toward a stronger answer."""


def build_evaluation_user_prompt(
    *,
    question: str,
    topic: str,
    expected_themes: tuple[str, ...],
    level: str,
    candidate_answer: str,
    doc_context: str,
) -> str:
    themes = ", ".join(expected_themes)
    return f"""Evaluate this mock interview answer.

**Interview level:** {level}
**Question topic:** {topic}
**Question:** {question}
**Expected themes to touch on:** {themes}

**Candidate answer:**
{candidate_answer}

**Retrieved Adobe documentation context:**
{doc_context}

Respond with ONLY valid JSON (no markdown fences) using this schema:
{{
  "score": <integer 1-5>,
  "score_pct": <integer 0-100>,
  "strengths": [<string>, ...],
  "gaps": [<string>, ...],
  "model_answer_outline": "<concise bullet-style outline of an ideal answer>",
  "feedback": "<2-3 paragraphs of coaching feedback in markdown>"
}}

Scoring guide:
1 = largely incorrect or off-topic
2 = partial understanding with major gaps
3 = adequate for the level with notable omissions
4 = strong answer with minor gaps
5 = excellent, interview-ready depth for the level"""


def build_scenario_evaluation_user_prompt(
    *,
    question: str,
    grading_rubric: dict,
    level: str,
    candidate_answer: str,
    doc_context: str,
) -> str:
    """Scenario questions are graded from a structured, weighted rubric rather
    than a holistic 1-5 self-assessment — the model's only job is to judge
    which rubric points the answer actually covers; scoring itself is computed
    deterministically from those judgments (see _score_from_rubric_match)."""
    points = (grading_rubric.get("required_points") or grading_rubric.get("partial_credit_points") or [])
    points_list = "\n".join(f"{i+1}. {p['point']}" for i, p in enumerate(points))

    return f"""Evaluate this mock interview answer to a scenario/troubleshooting question against a fixed rubric.

**Interview level:** {level}
**Question:** {question}

**Rubric points to check for** (does the candidate's answer cover each, even if worded differently?):
{points_list}

**Candidate answer:**
{candidate_answer}

**Retrieved Adobe documentation context:**
{doc_context}

For each numbered rubric point, judge whether the candidate's answer covers it — credit the underlying idea even if phrased differently, don't require exact wording.

Respond with ONLY valid JSON (no markdown fences) using this schema:
{{
  "matched_points": [
    {{"point": "<exact rubric point text>", "matched": <true|false>, "evidence": "<short quote or paraphrase from the answer, or empty string if not matched>"}}
  ],
  "feedback": "<2-3 paragraphs of coaching feedback in markdown, referencing which points were covered and which were missed>"
}}

Include every rubric point listed above in matched_points, in the same order, with the exact same point text."""


def build_followup_detection_prompt(
    *,
    question: str,
    topic: str,
    level: str,
    candidate_answer: str,
    doc_context: str,
) -> str:
    return f"""You are triaging a mock interview answer to decide if it needs a follow-up question.

**Interview level:** {level}
**Question topic:** {topic}
**Question:** {question}

**Candidate answer:**
{candidate_answer}

**Reference Adobe documentation context:**
{doc_context}

Is this answer thin (too short/vague to demonstrate understanding) or off-target
(doesn't address what was asked) for a candidate at the **{level}** level?

Respond with ONLY a single word: WEAK or OK. Do not explain."""


def build_followup_generation_prompt(
    *,
    question: str,
    topic: str,
    level: str,
    candidate_answer: str,
    doc_context: str,
) -> str:
    return f"""The candidate gave a thin or off-target answer to this mock interview question.

**Interview level:** {level}
**Question topic:** {topic}
**Original question:** {question}

**Candidate answer:**
{candidate_answer}

**Reference Adobe documentation context:**
{doc_context}

Write ONE targeted follow-up question that probes the same topic more deeply or
redirects the candidate toward what the original question actually asked. It
should be answerable from the same subject area — do not introduce a new topic.

Respond with ONLY the follow-up question text, no preamble, no quotes."""


def build_session_evaluation_prompt(
    *,
    level: str,
    profile_id: str,
    per_question_results: list[dict],
) -> str:
    focus = profile_label(level, profile_id)
    blocks: list[str] = []
    for i, row in enumerate(per_question_results, 1):
        blocks.append(
            f"### Question {i}: {row['question']}\n"
            f"**Topic:** {row['topic']}\n"
            f"**Candidate answer:** {row['answer']}\n"
            f"**Score:** {row.get('score', 'N/A')}/5\n"
            f"**Strengths:** {', '.join(row.get('strengths') or []) or '—'}\n"
            f"**Gaps:** {', '.join(row.get('gaps') or []) or '—'}"
        )
    qa_block = "\n\n".join(blocks)

    return f"""Synthesize a final mock interview debrief for a **{level}** candidate focused on **{focus}**.

Per-question evaluations:
{qa_block}

Respond with ONLY valid JSON (no markdown fences):
{{
  "readiness": "<one of: not_ready | needs_work | nearly_ready | interview_ready>",
  "readiness_summary": "<1-2 sentences on overall interview readiness>",
  "strengths": [<string>, ...],
  "priority_gaps": [<string>, ...],
  "mistakes_to_avoid": [<string>, ...],
  "topics_to_read": [
    {{ "topic": "<string>", "reason": "<why study this>", "source_question_indices": [<the Question N number(s) above that this topic draws from>] }}
  ],
  "overall_feedback": "<3-5 paragraphs of honest, coaching feedback in markdown covering answer quality, depth vs level, and concrete next steps>"
}}

Note: the numeric overall score is computed separately from your per-question scores above — do not include it here.

Be direct and honest. Call out patterns (e.g. UI-only answers without concepts, missing trade-offs, weak cross-product reasoning)."""


def build_welcome_message(level: str, profile_id: str, question_count: int) -> str:
    focus = profile_label(level, profile_id)
    return (
        f"**Interviewer Mode** — {level.title()} · {focus}\n\n"
        f"I'll ask you **{question_count}** practice questions tailored to this profile. "
        "Answer each in your own words as you would in a real interview.\n\n"
        "**How this works:**\n"
        "1. Read the question, then answer in the editor — type it out, or click the mic to dictate and have it "
        "transcribed for you.\n"
        "2. Use **Markdown** for structure — headings, bullets, and **bold** for key terms. If you dictated your "
        "answer, skim the transcript first — it can misspell product names or miss words — and fix it up before saving.\n"
        "3. Click **Save answer**, then review — you can **edit** before moving on.\n"
        "4. After all questions, you'll **review every answer** once more, then submit for evaluation.\n"
        "5. You'll receive an honest debrief: scores, interview readiness, topics to read, and mistakes to avoid.\n\n"
        "When you're ready, read the question and start writing your answer below."
    )
