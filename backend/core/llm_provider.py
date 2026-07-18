"""
LLM provider toggle — in-memory cache with 30s TTL backed by system_config
PostgreSQL table. Same pattern as kill_switch.py.

Switches the main answer-generation chain (Haiku/Sonnet) between AWS Bedrock
(ChatBedrockConverse, default) and the direct Anthropic API (ChatAnthropic).
Retrieval (Titan embeddings) is unaffected either way — this only changes
generation.

Only consulted for admin requests (see rag_pipeline._current_llm_provider) —
non-admin traffic always uses Bedrock regardless of this setting, so this
toggle exists purely to let the admin flip back to direct Anthropic for
testing/debugging.

Usage:
  get_llm_provider()      → "anthropic" | "bedrock" (cached, 30s TTL)
  set_llm_provider(value) → writes to DB and invalidates cache
"""

import time

_CACHE_TTL = 30.0
_KEY = "llm_provider"
_VALID = ("anthropic", "bedrock")
_DEFAULT = "bedrock"

_cache: dict = {"provider": _DEFAULT, "expires_at": 0.0}


def get_llm_provider() -> str:
    now = time.monotonic()
    if now < _cache["expires_at"]:
        return _cache["provider"]

    try:
        from backend.core import google_db
        raw = (google_db.get_system_config(_KEY) or _DEFAULT).strip().lower()
        provider = raw if raw in _VALID else _DEFAULT
    except Exception:
        provider = _DEFAULT  # fail to the known-working default

    _cache["provider"] = provider
    _cache["expires_at"] = now + _CACHE_TTL
    return provider


def set_llm_provider(provider: str) -> None:
    provider = provider.strip().lower()
    if provider not in _VALID:
        raise ValueError(f"llm_provider must be one of {_VALID}, got {provider!r}")
    from backend.core import google_db
    google_db.set_system_config(_KEY, provider)
    _cache["expires_at"] = 0.0  # invalidate immediately
