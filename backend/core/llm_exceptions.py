"""
Normalized exception types for LLM calls, shared across providers.

Both BedrockMessagesClient (bedrock_messages.py) and AnthropicMessagesClient
(anthropic_messages.py) translate their provider-specific exceptions into
these before raising, so callers (groundedness.py, interviewer_pipeline.py,
chat.py) can catch one set of types regardless of which provider is
currently selected via LLM_PROVIDER. Without this, an error-handling branch
written and tested only against Bedrock's exception shapes would silently
never be exercised in local dev mode (direct-Anthropic), and could fail
differently the first time it hits Bedrock in production.
"""

from __future__ import annotations


class ProviderError(Exception):
    """Base type for any LLM provider failure that isn't a rate limit or
    content filter. Wraps the original provider-specific exception."""

    def __init__(self, message: str, *, original: Exception | None = None) -> None:
        super().__init__(message)
        self.original = original


class RateLimitError(ProviderError):
    """Provider rejected the request due to rate/throughput limits
    (Bedrock ThrottlingException / TooManyRequestsException, Anthropic
    429 RateLimitError)."""


class ContentFilterError(ProviderError):
    """Provider blocked or truncated the response due to content filtering
    (Bedrock Converse stopReason == "content_filtered", Anthropic
    stop_reason == "refusal")."""
