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

# The only two Anthropic model ids referenced anywhere in this codebase.
_MODEL_MAP = {
    "claude-sonnet-4-6": "global.anthropic.claude-sonnet-4-6",
    "claude-haiku-4-5-20251001": "global.anthropic.claude-haiku-4-5-20251001-v1:0",
}


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
        resp = await asyncio.to_thread(self._bedrock.converse, **kwargs)
        text = resp["output"]["message"]["content"][0]["text"]
        return SimpleNamespace(content=[SimpleNamespace(text=text)])


class BedrockMessagesClient:
    """Duck-types the subset of AsyncAnthropic's interface (.messages.create)
    that this codebase actually calls."""

    def __init__(self, region_name: str = "us-east-1") -> None:
        self.messages = _Messages(boto3.client("bedrock-runtime", region_name=region_name))
