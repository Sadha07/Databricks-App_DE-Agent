"""Unit tests for individual nodes with fabricated state."""

from __future__ import annotations

from typing import Any

from de_agent.agent.nodes.environment_setup import environment_setup_node
from de_agent.agent.nodes.planning import planning_node
from de_agent.agent.nodes.profiling import profiling_node
from de_agent.agent.state import new_state


def _base_state(b64: str) -> dict[str, Any]:
    return dict(
        new_state(
            run_id="t1",
            business_instruction="",
            dataset={"name": "orders", "source_filename": "orders.csv"},
            raw_bytes_b64=b64,
            require_approval=False,
        )
    )


def test_environment_setup_provisions_scope(dummy_csv_b64: str, graph_config: dict[str, Any]) -> None:
    state = _base_state(dummy_csv_b64)
    update = environment_setup_node(state, graph_config)
    assert update["catalog"] == "de_agent_test"
    assert update["schema_name"] == "orders"
    assert update["landing_table"].endswith(".landing_orders")


def test_profiling_populates_profile(dummy_csv_b64: str, graph_config: dict[str, Any]) -> None:
    state = _base_state(dummy_csv_b64)
    update = profiling_node(state, graph_config)
    assert update["profile"]["row_count"] == 8


def test_planning_builds_bronze_and_silver(dummy_csv_b64: str, graph_config: dict[str, Any]) -> None:
    state = _base_state(dummy_csv_b64)
    state.update({"catalog": "de_agent_test", "schema_name": "orders"})
    state.update(profiling_node(state, graph_config))
    update = planning_node(state, graph_config)
    layers = [layer["layer"] for layer in update["execution_plan"]["layers"]]
    assert layers == ["bronze", "silver"]
