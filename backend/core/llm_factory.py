"""
Single point where the LLM_PROVIDER setting is consulted. Every call site
that needs an LLM — the LangChain chains in rag_pipeline.py, and the raw
messages-API clients used by groundedness.py, interviewer_pipeline.py, and
chat.py's follow-ups endpoint — routes through get_chat_model() or
get_messages_client() instead of branching on provider itself.
"""

from __future__ import annotations

from typing import Literal

from langchain_anthropic import ChatAnthropic
from langchain_aws import ChatBedrockConverse

from backend.core.anthropic_messages import AnthropicMessagesClient
from backend.core.bedrock_messages import BedrockMessagesClient
from config.settings import Settings

# Logical model name -> (direct-Anthropic id, Bedrock id). The Bedrock id
# carries the "global.anthropic." prefix / "-v1:0" suffix; both point at the
# same underlying model.
_MODEL_IDS: dict[str, tuple[str, str]] = {
    "haiku": ("claude-haiku-4-5-20251001", "global.anthropic.claude-haiku-4-5-20251001-v1:0"),
    "sonnet": ("claude-sonnet-4-6", "global.anthropic.claude-sonnet-4-6"),
}


def get_chat_model(size: Literal["haiku", "sonnet"], settings: Settings, max_tokens: int):
    """A LangChain chat model for `size`, chosen per settings.llm_provider.
    ChatAnthropic and ChatBedrockConverse both implement BaseChatModel, so
    callers can pipe either into the same LCEL chain unchanged."""
    anthropic_id, bedrock_id = _MODEL_IDS[size]
    if settings.llm_provider == "bedrock":
        return ChatBedrockConverse(model_id=bedrock_id, region_name=settings.bedrock_region, max_tokens=max_tokens)
    return ChatAnthropic(model=anthropic_id, api_key=settings.anthropic_api_key, max_tokens=max_tokens, streaming=True)


def get_messages_client(settings: Settings):
    """The raw messages-API client (BedrockMessagesClient or
    AnthropicMessagesClient) chosen per settings.llm_provider. Both duck-type
    AsyncAnthropic's `.messages.create(...)` interface identically, including
    the `usage` field on the response."""
    if settings.llm_provider == "bedrock":
        return BedrockMessagesClient(region_name=settings.bedrock_region)
    return AnthropicMessagesClient(api_key=settings.anthropic_api_key)
