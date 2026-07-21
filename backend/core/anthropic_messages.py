"""
Direct-Anthropic-API sibling of BedrockMessagesClient — same duck-typed
`.messages.create(...)` interface, so call sites written against either
client don't need to branch on provider themselves (see llm_factory.py).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import anthropic

from backend.core.llm_exceptions import ContentFilterError, ProviderError, RateLimitError


class _Messages:
    def __init__(self, client: anthropic.AsyncAnthropic) -> None:
        self._client = client

    async def create(
        self,
        *,
        model: str,
        max_tokens: int,
        messages: list[dict],
        system: str | None = None,
    ) -> Any:
        kwargs: dict[str, Any] = {"model": model, "max_tokens": max_tokens, "messages": messages}
        if system:
            kwargs["system"] = system
        try:
            resp = await self._client.messages.create(**kwargs)
        except anthropic.RateLimitError as exc:
            raise RateLimitError(f"Anthropic rate limit: {exc}", original=exc) from exc
        except anthropic.AnthropicError as exc:
            # True SDK root (APIError, plus anything else the SDK might raise
            # before/around the request) — see bedrock_messages.py's
            # analogous BotoCoreError fix for why the assumed common base
            # isn't always the actual one.
            raise ProviderError(f"Anthropic API error: {exc}", original=exc) from exc

        if resp.stop_reason == "refusal":
            raise ContentFilterError("Anthropic response blocked by content filtering (stop_reason=refusal)")

        text = resp.content[0].text if resp.content else ""
        return SimpleNamespace(
            content=[SimpleNamespace(text=text)],
            usage=SimpleNamespace(
                input_tokens=resp.usage.input_tokens,
                output_tokens=resp.usage.output_tokens,
            ),
        )


class AnthropicMessagesClient:
    """Duck-types the subset of AsyncAnthropic's interface (.messages.create)
    that this codebase actually calls — mirrors BedrockMessagesClient's shape
    exactly, including the `usage` field on the returned response, so a
    future cost-logging or caching feature can read it identically regardless
    of provider."""

    def __init__(self, api_key: str | None) -> None:
        self.messages = _Messages(anthropic.AsyncAnthropic(api_key=api_key))
