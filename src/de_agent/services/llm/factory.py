"""LLM factory with per-node model routing.

Simple SQL generation can run on a cheaper/faster model; the Gold reasoning and
planning nodes route to a stronger model. Swapping providers (Groq <-> Databricks)
is a config change, never a code change in the nodes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from de_agent.config.settings import LLMProvider
from de_agent.services.llm.base import LLMClient
from de_agent.services.llm.fake import FakeLLMClient

if TYPE_CHECKING:
    from de_agent.config.settings import Settings

# Nodes that benefit from the stronger reasoning model.
_REASONING_NODES = frozenset({"gold_reasoning", "gold_planning", "planning"})


class LLMFactory:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._cache: dict[str, LLMClient] = {}

    def for_node(self, node: str) -> LLMClient:
        key = "reasoning" if node in _REASONING_NODES else "default"
        if key not in self._cache:
            self._cache[key] = self._build(reasoning=key == "reasoning")
        return self._cache[key]

    def _build(self, *, reasoning: bool) -> LLMClient:
        provider = self._settings.llm.provider
        if provider is LLMProvider.FAKE:
            return FakeLLMClient()
        if provider is LLMProvider.GROQ:
            from de_agent.services.llm.groq_client import GroqClient

            model = (
                self._settings.llm.groq_model_reasoning
                if reasoning
                else self._settings.llm.groq_model
            )
            return GroqClient(api_key=self._settings.llm.groq_api_key, model=model)
        if provider is LLMProvider.DATABRICKS:
            from de_agent.services.llm.databricks_client import DatabricksLLMClient

            return DatabricksLLMClient(
                self._settings, endpoint=self._settings.databricks.llm_endpoint
            )
        raise ValueError(f"Unknown LLM provider: {provider}")
