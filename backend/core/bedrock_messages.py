"""
Drop-in replacement for `AsyncAnthropic().messages.create(...)` backed by AWS
Bedrock Converse, so call sites written against the Anthropic Messages API
shape (model, max_tokens, messages, system) don't need to change beyond
swapping the client construction.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from backend.core.llm_exceptions import ContentFilterError, ProviderError, RateLimitError

# The only two Anthropic model ids referenced anywhere in this codebase.
_MODEL_MAP = {
    "claude-sonnet-4-6": "global.anthropic.claude-sonnet-4-6",
    "claude-haiku-4-5-20251001": "global.anthropic.claude-haiku-4-5-20251001-v1:0",
}

_THROTTLING_CODES = {"ThrottlingException", "TooManyRequestsException"}


class _Messages:
    def __init__(self, bedrock) -> None:
        self._bedrock = bedrock

    async def create(
        self,
        *,
        model: str,
        max_tokens: int,
        messages: list[dict],
        system: str | None = None,
    ) -> Any:
        model_id = _MODEL_MAP.get(model, model)
        converse_messages = [
            {"role": m["role"], "content": [{"text": m["content"]}]} for m in messages
        ]
        kwargs = {
            "modelId": model_id,
            "messages": converse_messages,
            "inferenceConfig": {"maxTokens": max_tokens},
        }
        if system:
            kwargs["system"] = [{"text": system}]
        try:
            resp = await asyncio.to_thread(self._bedrock.converse, **kwargs)
        except ClientError as exc:
            # Server-side rejection (the request reached Bedrock) — includes
            # throttling.
            code = exc.response.get("Error", {}).get("Code", "")
            if code in _THROTTLING_CODES:
                raise RateLimitError(f"Bedrock throttled: {exc}", original=exc) from exc
            raise ProviderError(f"Bedrock Converse error: {exc}", original=exc) from exc
        except BotoCoreError as exc:
            # Client-side rejection before any request was sent (e.g.
            # ParamValidationError, NoCredentialsError) — does not inherit
            # from ClientError, so needs its own translation, not just a
            # narrower except clause.
            raise ProviderError(f"Bedrock request error: {exc}", original=exc) from exc

        if resp.get("stopReason") == "content_filtered":
            raise ContentFilterError("Bedrock response blocked by content filtering (stopReason=content_filtered)")

        text = resp["output"]["message"]["content"][0]["text"]
        usage = resp.get("usage", {})
        return SimpleNamespace(
            content=[SimpleNamespace(text=text)],
            usage=SimpleNamespace(
                input_tokens=usage.get("inputTokens", 0),
                output_tokens=usage.get("outputTokens", 0),
            ),
        )


class BedrockMessagesClient:
    """Duck-types the subset of AsyncAnthropic's interface (.messages.create)
    that this codebase actually calls."""

    def __init__(self, region_name: str = "us-east-1") -> None:
        self.messages = _Messages(boto3.client("bedrock-runtime", region_name=region_name))
