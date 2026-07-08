"""Shared test fixtures."""

from __future__ import annotations

import base64
from pathlib import Path

import pytest

from de_agent.config.settings import (
    DatabricksSettings,
    Environment,
    LLMProvider,
    LLMSettings,
    Settings,
)
from de_agent.services.container import AppContainer

_FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def dummy_csv_bytes() -> bytes:
    return (_FIXTURES / "dummy_orders.csv").read_bytes()


@pytest.fixture
def dummy_csv_b64(dummy_csv_bytes: bytes) -> str:
    return base64.b64encode(dummy_csv_bytes).decode("ascii")


@pytest.fixture
def settings() -> Settings:
    return Settings(
        environment=Environment.LOCAL,
        require_approval=False,
        target_catalog="de_agent_test",
        allow_create_catalog=True,
        max_retries=2,
        databricks=DatabricksSettings(),
        llm=LLMSettings(provider=LLMProvider.FAKE),
    )


@pytest.fixture
def container(settings: Settings) -> AppContainer:
    return AppContainer(settings)


@pytest.fixture
def graph_config(container: AppContainer):
    return {"configurable": {"thread_id": "test-thread", **container.as_config_value()}}
