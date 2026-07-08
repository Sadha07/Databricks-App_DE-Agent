"""Databricks Model Serving LLM client (Claude / Llama / DBRX via a serving endpoint).

Preferred for production: calls stay inside the workspace, governed and billed
through Databricks, no external egress. Uses the OpenAI-compatible chat interface
exposed by ``WorkspaceClient.serving_endpoints``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from de_agent.config.logging import get_logger
from de_agent.services.llm.base import LLMResponse

if TYPE_CHECKING:
    from de_agent.config.settings import Settings

log = get_logger(__name__)


class DatabricksLLMClient:
    def __init__(self, settings: Settings, endpoint: str) -> None:
        from databricks.sdk import WorkspaceClient

        self._endpoint = endpoint
        if settings.databricks.host and settings.databricks.token:
            self._w = WorkspaceClient(
                host=settings.databricks.host, token=settings.databricks.token
            )
        else:
            self._w = WorkspaceClient()

    def complete(
        self,
        *,
        system: str,
        prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        from databricks.sdk.service.serving import ChatMessage, ChatMessageRole

        resp = self._w.serving_endpoints.query(
            name=self._endpoint,
            messages=[
                ChatMessage(role=ChatMessageRole.SYSTEM, content=system),
                ChatMessage(role=ChatMessageRole.USER, content=prompt),
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        text = ""
        if resp.choices:
            msg = resp.choices[0].message
            text = (msg.content if msg else "") or ""
        usage = resp.usage
        log.info("llm.complete", provider="databricks", endpoint=self._endpoint)
        return LLMResponse(
            text=text,
            model=self._endpoint,
            prompt_tokens=getattr(usage, "prompt_tokens", 0) if usage else 0,
            completion_tokens=getattr(usage, "completion_tokens", 0) if usage else 0,
        )
