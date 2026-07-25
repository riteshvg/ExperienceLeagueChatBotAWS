"""
Live smoke test for the LLM_PROVIDER switch (backend/core/llm_factory.py).

Run this with a real .env loaded (ANTHROPIC_API_KEY, AWS creds, DATABASE_URL)
and the backend server NOT required to be running for Part A/C — those call
the clients/pipeline directly. Part B instructions hit a running server for
the full endpoint-level check the task actually asked for.

Usage:
    python -m scripts.smoke_test_llm_provider

Run it once with LLM_PROVIDER=anthropic in your .env, then again with
LLM_PROVIDER=bedrock (edit .env between runs — the setting is read once at
import time via config.settings.get_settings()).
"""

from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import get_settings  # noqa: E402
from backend.core.llm_factory import get_chat_model, get_messages_client  # noqa: E402
from backend.core.llm_exceptions import ProviderError, RateLimitError, ContentFilterError  # noqa: E402


async def part_a_messages_client():
    settings = get_settings()
    print(f"\n=== Part A: get_messages_client() — LLM_PROVIDER={settings.llm_provider} ===")
    client = get_messages_client(settings)
    print(f"Client type: {type(client).__name__}")

    resp = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=50,
        messages=[{"role": "user", "content": "Reply with exactly the word: PONG"}],
    )
    text = resp.content[0].text
    print(f"Response text: {text!r}")
    print(f"usage: input_tokens={resp.usage.input_tokens} output_tokens={resp.usage.output_tokens}")
    assert "PONG" in text.upper(), "FAIL: model did not echo expected text"
    assert resp.usage.input_tokens > 0 and resp.usage.output_tokens > 0, "FAIL: usage not populated"
    print("PASS: real response + usage populated")


async def part_a2_chat_model():
    settings = get_settings()
    print(f"\n=== Part A2: get_chat_model('haiku') — LLM_PROVIDER={settings.llm_provider} ===")
    llm = get_chat_model("haiku", settings, max_tokens=50)
    print(f"LangChain model type: {type(llm).__name__}")
    result = await llm.ainvoke("Reply with exactly the word: PONG")
    text = result.content if isinstance(result.content, str) else str(result.content)
    print(f"Response text: {text!r}")
    assert "PONG" in text.upper(), "FAIL: chat model did not echo expected text"
    print("PASS: LangChain chat model returns real response for this provider")


async def part_c_error_injection():
    """Deliberately trigger a provider error and confirm it surfaces as the
    normalized type, not the raw anthropic/boto3 exception."""
    settings = get_settings()
    print(f"\n=== Part C: error-injection — LLM_PROVIDER={settings.llm_provider} ===")
    client = get_messages_client(settings)

    # Malformed request: an unknown model id is rejected by both providers as
    # a real 4xx (Anthropic: NotFoundError; Bedrock: ValidationException) —
    # exercises the translation layer rather than just a connection error.
    # (max_tokens=0 was tried first and rejected as invalid by Bedrock, but
    # Anthropic's direct API accepts it and just returns 0 output tokens —
    # not a reliable trigger across both providers.)
    try:
        await client.messages.create(
            model="does-not-exist-model",
            max_tokens=50,
            messages=[{"role": "user", "content": "hi"}],
        )
        print("FAIL: expected an exception for an unknown model id, got a response instead")
    except (RateLimitError, ContentFilterError, ProviderError) as exc:
        print(f"PASS: caught normalized type {type(exc).__name__}: {exc}")
        print(f"      original provider exception type: {type(exc.original).__name__ if exc.original else None}")
    except Exception as exc:
        print(f"FAIL: raw provider exception leaked past translation layer: {type(exc).__module__}.{type(exc).__name__}: {exc}")
        raise


async def main():
    settings = get_settings()
    print(f"LLM_PROVIDER = {settings.llm_provider!r}")
    if settings.llm_provider not in ("anthropic", "bedrock"):
        print("Set LLM_PROVIDER=anthropic or LLM_PROVIDER=bedrock in .env before running.")
        return
    await part_a_messages_client()
    await part_a2_chat_model()
    await part_c_error_injection()
    print("\nAll direct-client checks completed for this provider. Re-run with the other LLM_PROVIDER value.")
    print("Then follow scripts/smoke_test_endpoints.md for the endpoint-level (Part B) and SSE (Part D) checks.")


if __name__ == "__main__":
    asyncio.run(main())
