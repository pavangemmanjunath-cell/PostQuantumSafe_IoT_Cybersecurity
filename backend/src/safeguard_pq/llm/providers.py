"""Provider-agnostic LLM access over plain HTTP.

Configured through environment variables (see ``.env.example``):

* ``LLM_PROVIDER=none`` (default) — no network calls; deterministic report.
* ``LLM_PROVIDER=openai_compatible`` — any OpenAI-style ``/chat/completions``
  endpoint (OpenAI, Azure-compatible gateways, Ollama, vLLM, LM Studio, …).
* ``LLM_PROVIDER=anthropic`` — Anthropic Messages API.

The LLM is only used to phrase the executive narrative. It never decides the
verdict, the score or the remediation plan, and it only receives redacted,
aggregated findings (never raw prompts, device logs or patient data).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import httpx

from ..config import Settings


class LLMError(Exception):
    pass


class LLMProvider(ABC):
    name: str = "none"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def model(self) -> str | None:
        return self.settings.llm_model

    @abstractmethod
    async def complete(self, system: str, user: str) -> str: ...


class NullProvider(LLMProvider):
    name = "none"

    async def complete(self, system: str, user: str) -> str:
        raise LLMError("LLM disabled")


class OpenAICompatibleProvider(LLMProvider):
    name = "openai_compatible"

    async def complete(self, system: str, user: str) -> str:
        s = self.settings
        base = (s.llm_base_url or "https://api.openai.com/v1").rstrip("/")
        headers = {"content-type": "application/json"}
        if s.llm_api_key:
            headers["authorization"] = f"Bearer {s.llm_api_key.get_secret_value()}"
        body = {
            "model": s.llm_model,
            "temperature": 0.2,
            "max_tokens": s.llm_max_tokens,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }
        try:
            async with httpx.AsyncClient(timeout=s.llm_timeout_s) as client:
                r = await client.post(f"{base}/chat/completions", json=body, headers=headers)
                r.raise_for_status()
                return r.json()["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            raise LLMError(f"{self.name} request failed: {type(exc).__name__}") from exc


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    async def complete(self, system: str, user: str) -> str:
        s = self.settings
        if not s.llm_api_key:
            raise LLMError("LLM_API_KEY is required for the anthropic provider")
        base = (s.llm_base_url or "https://api.anthropic.com").rstrip("/")
        headers = {
            "content-type": "application/json",
            "x-api-key": s.llm_api_key.get_secret_value(),
            "anthropic-version": "2023-06-01",
        }
        body = {
            "model": s.llm_model,
            "max_tokens": s.llm_max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        try:
            async with httpx.AsyncClient(timeout=s.llm_timeout_s) as client:
                r = await client.post(f"{base}/v1/messages", json=body, headers=headers)
                r.raise_for_status()
                blocks = r.json().get("content", [])
                return "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise LLMError(f"{self.name} request failed: {type(exc).__name__}") from exc


def get_provider(settings: Settings) -> LLMProvider:
    if not settings.llm_enabled:
        return NullProvider(settings)
    if settings.llm_provider == "anthropic":
        return AnthropicProvider(settings)
    return OpenAICompatibleProvider(settings)
