"""Dependency container.

Builds and holds the service instances for a run, choosing real vs. fake
implementations based on settings. A single ``AppContainer`` is created by the UI
and threaded into the graph via LangGraph's ``config["configurable"]`` so nodes
resolve their dependencies without importing concrete implementations.
"""

from __future__ import annotations

from langchain_core.runnables import RunnableConfig

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from de_agent.config.settings import Environment
from de_agent.services.artifacts import ArtifactStore, DocumentationBuilder, LineageBuilder
from de_agent.services.databricks.base import DatabricksService
from de_agent.services.databricks.fake import InMemoryDatabricksService
from de_agent.services.llm import LLMFactory
from de_agent.services.profiling import DatasetProfiler
from de_agent.services.validation import LayerValidator

if TYPE_CHECKING:
    from de_agent.config.settings import Settings

_CONFIG_KEY = "container"


class AppContainer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.databricks: DatabricksService = self._build_databricks(settings)
        self.llm = LLMFactory(settings)
        self.profiler = DatasetProfiler()
        self.validator = LayerValidator(self.databricks)
        self.documentation = DocumentationBuilder()
        self.lineage = LineageBuilder()
        artifact_dir = str(Path(tempfile.gettempdir()) / "de_agent_artifacts")
        self.artifacts = ArtifactStore(artifact_dir)

    @staticmethod
    def _build_databricks(settings: Settings) -> DatabricksService:
        if settings.environment is Environment.DATABRICKS or settings.databricks.host:
            from de_agent.services.databricks.service import SdkDatabricksService

            return SdkDatabricksService(settings)
        return InMemoryDatabricksService()

    def as_config_value(self) -> dict[str, object]:
        """Return the mapping to place under config['configurable']."""
        return {_CONFIG_KEY: self}


def get_container(config: RunnableConfig) -> AppContainer:
    """Resolve the container from a LangGraph runnable config."""
    configurable = config.get("configurable", {}) if config else {}
    container = configurable.get(_CONFIG_KEY) if isinstance(configurable, dict) else None
    if not isinstance(container, AppContainer):
        raise RuntimeError("AppContainer missing from graph config['configurable']")
    return container
