# Endpoint + SSE smoke test (manual)

Run this after `python -m scripts.smoke_test_llm_provider` passes for both
provider values. This part needs the real backend + frontend running, so it
can't be scripted from here — do it locally and report back what you
actually observed (not "should work").

For each of `LLM_PROVIDER=anthropic` and `LLM_PROVIDER=bedrock`:

## 1. Start the backend with that provider

```
LLM_PROVIDER=anthropic uvicorn backend.main:app --reload   # then repeat with =bedrock
```

Confirm no startup errors, and that `get_settings().llm_provider` in the logs
(or a quick `curl localhost:8000/api/admin/settings` with your admin token)
shows the value you set.

## 2. Main /chat (streaming) — call site: rag_pipeline.py

Start the frontend (`npm run dev` in `frontend/`) and, in a real browser tab,
ask a real Adobe Analytics/CJA/AEP question through the chat UI. Confirm:

- [ ] Tokens appear incrementally in the UI as they stream (not all at once) — this is the actual ask in item 4, not just that the final text is correct.
- [ ] The full answer is coherent, on-topic, and complete (not truncated mid-sentence).
- [ ] Citations render at the end.
- [ ] No error banner / no fallback "I don't have information" for a question you know is covered.

Repeat as an **admin** user (so the groundedness-check buffered path
triggers) for at least one query with weak/partial grounding, and confirm
the "reviewing" status message appears and the final answer still renders
correctly (this exercises `get_messages_client()` inside
`_apply_groundedness_ux`, not just `get_chat_model()`).

## 3. Interviewer Mode /submit — call site: interviewer_pipeline.py

Start an interview session, answer at least one question, submit for
grading. Confirm:

- [ ] Per-question score/feedback comes back populated (not the
      `"Evaluation service temporarily unavailable"` fallback text — if you
      see that, the client call failed silently; check backend logs for
      which exception fired).
- [ ] Session-level synthesis report renders (topics to read, overall
      feedback).

## 4. Follow-ups endpoint — call site: chat.py `/chat/follow-ups`

After a chat answer, confirm the 3 follow-up-question chips render in the
UI and are contextually relevant to what was just discussed (not empty —
an empty list is the silent-failure fallback in `get_follow_ups`).

## Report back

For each provider value, note pass/fail per numbered item above, and paste
any backend log lines showing exception types if something in item 2 or 3
fell back instead of returning a real answer.
