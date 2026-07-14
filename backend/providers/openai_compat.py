"""OpenAI-compatible adapter — covers OpenRouter and vLLM (Decision F).

OpenRouter is OpenAI-API-shaped, so the standard OpenAI SDK works by pointing ``base_url`` at it. A local
vLLM server exposes the same API → the *same* adapter, just a different ``OPENROUTER_BASE_URL``.
"""
from __future__ import annotations

from typing import Any

from openai import OpenAI

from ..config import get_settings


class OpenAICompatClient:
    def __init__(self) -> None:
        s = get_settings()
        self.model = s.llm_model
        # vLLM often needs no real key; a placeholder keeps the SDK happy.
        self._client = OpenAI(api_key=s.openrouter_api_key or "not-needed", base_url=s.openrouter_base_url)

    def complete_json(self, system: str, user: str, response_format: dict[str, Any]) -> str:
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format=response_format,  # structured-output request (best-effort on the free router)
            temperature=0,                    # determinism — same note → same extraction
        )
        return resp.choices[0].message.content or ""
