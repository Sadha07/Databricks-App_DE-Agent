"""Groq-backed LLM client (GPT-OSS / Llama), used for local + dummy-data testing."""

from __future__ import annotations

from de_agent.config.logging import get_logger
from de_agent.services.llm.base import LLMResponse

log = get_logger(__name__)


class GroqClient:
    def __init__(self, api_key: str, model: str) -> None:
        from groq import Groq

        self._client = Groq(api_key=api_key)
        self._model = model

    def complete(
        self,
        *,
        system: str,
        prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        resp = self._client.chat.completions.create(
            model=self._model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        )
        choice = resp.choices[0].message.content or ""
        usage = resp.usage
        log.info(
            "llm.complete",
            provider="groq",
            model=self._model,
            prompt_tokens=getattr(usage, "prompt_tokens", 0),
            completion_tokens=getattr(usage, "completion_tokens", 0),
        )
        return LLMResponse(
            text=choice,
            model=self._model,
            prompt_tokens=getattr(usage, "prompt_tokens", 0),
            completion_tokens=getattr(usage, "completion_tokens", 0),
        )
