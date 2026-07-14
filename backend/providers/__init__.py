"""LLM provider seam (Decision F / ADR-0007).

One tiny interface, selected by env ``LLM_PROVIDER``, so the extractor never knows which backend it's
talking to. ``openai_compat`` covers OpenRouter (Phase 1) and vLLM (Phase 3); ``bedrock`` covers Claude on
AWS (Phase 2). Adapters are imported lazily so an unused provider's deps/config are never required.
"""
from __future__ import annotations

from typing import Any, Protocol

from ..config import get_settings


class LLMClient(Protocol):
    model: str

    def complete_json(self, system: str, user: str, response_format: dict[str, Any]) -> str:
        """Return the model's raw text (expected to be the JSON object)."""
        ...


def get_llm_client() -> LLMClient:
    provider = get_settings().llm_provider
    if provider in ("openrouter", "vllm"):
        from .openai_compat import OpenAICompatClient
        return OpenAICompatClient()
    if provider == "bedrock":
        from .bedrock import BedrockClient  # Phase 2 — added with the Bedrock adapter
        return BedrockClient()
    raise ValueError(f"unknown LLM_PROVIDER: {provider}")
