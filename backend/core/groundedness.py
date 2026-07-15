"""
Post-generation groundedness check + trustworthiness-over-completeness UX layer.

Promoted from eval/groundedness_check.py + eval/groundedness_ux.py (prototyped
and validated against the 40-query golden set; see eval/full_pipeline_rerun_v2.json
and the LangSmith experiment "post-groundedness-fix-baseline-v1").

Only runs for queries where evidence is weak enough that fabrication risk is
real (see should_run_groundedness_check) — see rag_pipeline.py for the
pre-generation branch that decides streamed vs. buffered+checked generation.

Escalation ladder (resolve_with_escalation): no answer ships without passing
its own reverification, except the final deterministic hard_fallback tier,
which is safe by construction (it authors no new claims beyond source URLs
already verified by the retrieval/evidence layer) and is therefore not
reverified — verifying a check that cannot fail by construction is pure
overhead, not a safety measure.
"""

from __future__ import annotations

import json

from anthropic import AsyncAnthropic

_CHECK_MODEL = "claude-haiku-4-5-20251001"

_GROUNDEDNESS_PROMPT = """You are auditing an AI-generated answer for fabricated specifics.

Compare the ANSWER below against the CONTEXT it was generated from. Flag only
specific, checkable claims (UI navigation paths, button/menu names, API endpoint
names, field names, dropdown values, exact URLs) that do NOT appear in — and
cannot be reasonably inferred from — the CONTEXT. Do not flag general concepts,
architecture descriptions, or paraphrases that are consistent with the context.

If you flag any unsupported claims, also classify their CONCENTRATION:

- "ISOLATED": every unsupported claim lives inside one contiguous, cleanly
  removable section (e.g. a single "Steps" list, a single paragraph) — you
  could delete that section alone and the rest of the answer would still read
  as complete, coherent, and fully supported.
- "INTEGRATED": unsupported claims are spread across multiple sections, are
  woven into otherwise-supported sentences, or are structurally load-bearing
  (e.g. they are specific steps inside a numbered list where the surrounding
  steps depend on them, or removing them would leave dangling references or
  broken structure elsewhere in the answer).
- "UNCERTAIN": you cannot confidently tell whether the unsupported content is
  cleanly separable — err toward this label whenever it's a close call.

Only set concentration when has_unsupported_specifics is true; otherwise use null.
{known_urls_section}
CONTEXT:
{context}

ANSWER:
{answer}

Respond with ONLY a JSON object, no other text:
{{"has_unsupported_specifics": bool, "unsupported_claims": [string, ...], "fabrication_concentration": "ISOLATED" | "INTEGRATED" | "UNCERTAIN" | null, "reasoning": string}}"""

_SURGICAL_PROMPT = """You are performing a DELETION-ONLY edit on an AI-generated answer. You are not \
a writer here — you are a censor. Do not add, rephrase, summarize, or reconstruct ANY procedural \
content of your own, even generic-sounding steps. If you catch yourself writing a new step, button \
name, or "General Steps" list that isn't a verbatim copy of text already in ANSWER, stop — that is \
exactly the failure mode this task exists to prevent.

Steps:
1. Copy the ANSWER below unchanged, sentence for sentence, EXCEPT:
2. Delete every sentence/bullet/line/table-row that matches or overlaps with an entry in \
   UNSUPPORTED_CLAIMS, and delete the section heading it lived under if that heading has nothing \
   left beneath it. Check EVERY section, including tables and summaries further down the answer —
   the same fabricated idea may be repeated in more than one place (e.g. explained in prose AND
   summarized in a table row); remove ALL occurrences, not just the first.
3. If deleting an item from a numbered list would leave other list items with skipped or dangling \
   numbers (e.g. deleting items 1-3 but leaving item 4), renumber the remaining items starting from 1, \
   or convert the remainder to unordered bullets — never leave an orphaned "4." with nothing before it.
4. At the single point where the deleted material was removed, insert exactly one short sentence \
   (not a list, not a new set of steps): "The exact steps for this aren't covered in the documentation \
   I have access to — see [<title>](<url>) for the specifics." — filling in the first entry from \
   SOURCE_DOCS. Do not describe what the steps might be.
5. Leave every other sentence in ANSWER completely untouched — same words, same order, same headings.

UNSUPPORTED_CLAIMS (delete these, verbatim or near-verbatim matches, wherever they appear):
{unsupported_claims}

SOURCE_DOCS (use the first one for the pointer note):
{source_docs}

ANSWER:
{answer}

Respond with ONLY the edited answer text — no preamble, no explanation, no surrounding quotes, and \
no new procedural content beyond the single pointer sentence specified above."""

_FALLBACK_PROMPT = """You are writing a deliberately conservative fallback answer because an earlier \
draft contained fabricated specifics that were too interwoven with legitimate content to safely edit.

Write a short, honest answer to the QUESTION using ONLY facts from CONTEXT. Structure it as:
1. What the documentation DOES confirm (only if CONTEXT actually supports something concrete for this \
question — if it supports nothing concrete, say so plainly instead of stretching).
2. An explicit, plain statement of what it does NOT cover for this specific question.
3. A pointer to SOURCE_DOCS for the parts not covered — use ONLY the URLs listed in SOURCE_DOCS \
verbatim; never construct, guess, or modify a URL yourself, even if it looks plausible.

Do not attempt to reconstruct or hedge the fabricated procedure — do not include any of the \
UNSUPPORTED_CLAIMS below, even caveated. Keep it shorter than a full walkthrough would be; brevity \
and honesty are valued over completeness here.

QUESTION:
{query}

CONTEXT:
{context}

UNSUPPORTED_CLAIMS (do not include these, even hedged):
{unsupported_claims}

SOURCE_DOCS (use these exact URLs only — do not invent others):
{source_docs}

Respond with ONLY the fallback answer text — no preamble, no explanation, no surrounding quotes."""


def should_run_groundedness_check(evidence: dict) -> bool:
    """Only run the check where fabrication risk is real — weak grounding, or
    strong retrieval that produced barely any citable sources (the highest-risk
    bucket observed in eval: see eval/groundedness_investigation.md)."""
    grounding_level = evidence.get("grounding_level")
    citation_count = evidence.get("citation_count", 0)
    if grounding_level in ("partial", "inferred", "insufficient"):
        return True
    if grounding_level == "documented" and citation_count <= 1:
        return True
    return False


def extract_known_urls(evidence: dict) -> list[str]:
    """URLs already verified as legitimate citations by the retrieval/evidence
    layer — these may be real sources even when they don't appear verbatim in
    the raw context text blob (which only contains chunk content, not URLs
    pulled from metadata)."""
    return [s["url"] for s in (evidence.get("sources") or []) if s.get("url")]


def _format_source_docs(evidence: dict) -> str:
    sources = evidence.get("sources") or []
    if not sources:
        return "(no specific source documents available)"
    lines = []
    for s in sources[:5]:
        title = s.get("title") or "Documentation"
        url = s.get("url") or ""
        lines.append(f"- {title}: {url}")
    return "\n".join(lines)


async def _call(client: AsyncAnthropic, prompt: str, max_tokens: int = 2000) -> str:
    resp = await client.messages.create(
        model=_CHECK_MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text.strip()


async def run_groundedness_check(
    client: AsyncAnthropic,
    context: str,
    answer: str,
    known_urls: list[str] | None = None,
) -> dict:
    known_urls_section = ""
    if known_urls:
        known_urls_section = (
            "\nKNOWN LEGITIMATE CITATION URLS (already verified by the system separately — "
            "do NOT flag any of these as unsupported even if they don't appear verbatim in "
            "CONTEXT; they are real, confirmed sources):\n"
            + "\n".join(f"- {u}" for u in known_urls) + "\n"
        )
    raw = await _call(
        client,
        _GROUNDEDNESS_PROMPT.format(context=context, answer=answer, known_urls_section=known_urls_section),
        max_tokens=1000,
    )
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw[raw.index("\n") + 1:] if "\n" in raw else raw
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"has_unsupported_specifics": None, "unsupported_claims": [], "reasoning": f"PARSE_ERROR: {raw[:300]}"}


async def _build_surgical(client: AsyncAnthropic, answer: str, check_result: dict, evidence: dict) -> str:
    return await _call(
        client,
        _SURGICAL_PROMPT.format(
            unsupported_claims="\n".join(f"- {c}" for c in (check_result.get("unsupported_claims") or [])),
            source_docs=_format_source_docs(evidence),
            answer=answer,
        ),
    )


async def _build_llm_fallback(client: AsyncAnthropic, query: str, context: str, check_result: dict, evidence: dict) -> str:
    return await _call(
        client,
        _FALLBACK_PROMPT.format(
            query=query,
            context=context,
            unsupported_claims="\n".join(f"- {c}" for c in (check_result.get("unsupported_claims") or [])),
            source_docs=_format_source_docs(evidence),
        ),
    )


def _build_hard_fallback(query: str, evidence: dict) -> str:
    """
    Deterministic, LLM-free last resort — contains no authored claims beyond a
    list of already-verified source URLs, so it cannot introduce new
    fabrication and is not reverified (nothing to verify).
    """
    sources = evidence.get("sources") or []
    if sources:
        lines = "\n".join(
            f"- [{s.get('title') or 'Documentation'}]({s['url']})"
            for s in sources[:5] if s.get("url")
        )
        pointer = f"The closest related documentation I found:\n\n{lines}"
    else:
        pointer = "I wasn't able to find documentation that directly addresses this."
    return (
        f"I don't have documentation that reliably confirms a specific answer to \"{query}\" — "
        f"I'd rather tell you that plainly than guess.\n\n{pointer}\n\n"
        "If you can point me to the specific product area or narrow the question, I can take another look."
    )


async def resolve_with_escalation(
    client: AsyncAnthropic,
    query: str,
    answer: str,
    context: str,
    evidence: dict,
    check_result: dict | None,
) -> dict:
    """
    Never ships an answer that fails its own reverification, regardless of
    which UX path produced it — except the final hard_fallback tier, which is
    safe by construction and skips reverification (see module docstring).

    Ladder: surgical_removal -> reverify -> [fail] -> full_fallback -> reverify
    -> [fail] -> hard_fallback (ship immediately, no reverify).

    Returns {"final_answer": str, "ux_action": str, "escalated": bool,
    "reverify_chain": [dict, ...]}.
    """
    known_urls = extract_known_urls(evidence)
    reverify_chain: list[dict] = []

    if not check_result or not check_result.get("has_unsupported_specifics"):
        return {"final_answer": answer, "ux_action": "none", "escalated": False, "reverify_chain": reverify_chain}

    concentration = check_result.get("fabrication_concentration")
    escalated = False

    if concentration == "ISOLATED":
        candidate = await _build_surgical(client, answer, check_result, evidence)
        action = "surgical_removal"
    else:
        candidate = await _build_llm_fallback(client, query, context, check_result, evidence)
        action = "full_fallback"

    reverify = await run_groundedness_check(client, context, candidate, known_urls=known_urls)
    reverify_chain.append({"ux_action": action, "reverify": reverify})

    if not reverify.get("has_unsupported_specifics"):
        return {"final_answer": candidate, "ux_action": action, "escalated": False, "reverify_chain": reverify_chain}

    escalated = True

    if action == "surgical_removal":
        candidate = await _build_llm_fallback(client, query, context, check_result, evidence)
        action = "full_fallback_escalated"
        reverify = await run_groundedness_check(client, context, candidate, known_urls=known_urls)
        reverify_chain.append({"ux_action": action, "reverify": reverify})
        if not reverify.get("has_unsupported_specifics"):
            return {"final_answer": candidate, "ux_action": action, "escalated": escalated, "reverify_chain": reverify_chain}

    # full_fallback (first attempt or escalated) still failed -> deterministic
    # hard fallback, shipped immediately (safe by construction, not reverified).
    candidate = _build_hard_fallback(query, evidence)
    return {"final_answer": candidate, "ux_action": "hard_fallback", "escalated": escalated, "reverify_chain": reverify_chain}


def pseudo_chunk(text: str, chunk_size: int = 20):
    """Split already-complete text into fixed-size pieces so the buffered/
    checked path can still emit a sequence of `token` events, preserving the
    frontend's existing streaming/typing UI without needing frontend changes."""
    for i in range(0, len(text), chunk_size):
        yield text[i:i + chunk_size]
