"""End-to-end graph test with fakes + in-memory checkpointer.

Proves routing, the auto-retry loops, and the Gold confirmation interrupt/resume
all work without any cloud access. This is the primary regression net.
"""

from __future__ import annotations

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from de_agent.agent.graph import build_graph
from de_agent.agent.state import new_state
from de_agent.services.container import AppContainer


@pytest.mark.integration
def test_full_medallion_run(container: AppContainer, dummy_csv_b64: str) -> None:
    graph = build_graph(MemorySaver())
    config = {"configurable": {"thread_id": "run-1", **container.as_config_value()}}

    state = new_state(
        run_id="run-1",
        business_instruction="Build a sales star schema",
        dataset={"name": "orders", "source_filename": "orders.csv"},
        raw_bytes_b64=dummy_csv_b64,
        require_approval=False,  # skip SQL approval gates for the automated path
    )

    graph.invoke(state, config)

    # The run should pause at the Gold confirmation gate.
    snapshot = graph.get_state(config)
    interrupts = [t.interrupts[0].value for t in snapshot.tasks if t.interrupts]
    assert interrupts and interrupts[0]["type"] == "gold_confirmation"

    # Confirm and let it finish.
    graph.invoke(Command(resume="yes, proceed"), config)

    final = graph.get_state(config)
    assert not final.next  # completed
    tables = final.values["tables_by_layer"]
    assert set(tables) == {"bronze", "silver", "gold"}


@pytest.mark.integration
def test_sql_error_is_retried_and_recovers(container: AppContainer, dummy_csv_b64: str) -> None:
    # Force the first bronze SQL execution to fail; the loop must self-correct.
    container.databricks.fail_next_sql = "syntax error near FROM"  # type: ignore[attr-defined]
    graph = build_graph(MemorySaver())
    config = {"configurable": {"thread_id": "run-2", **container.as_config_value()}}
    state = new_state(
        run_id="run-2",
        business_instruction="",
        dataset={"name": "orders", "source_filename": "orders.csv"},
        raw_bytes_b64=dummy_csv_b64,
        require_approval=False,
    )
    graph.invoke(state, config)
    graph.invoke(Command(resume="yes"), config)
    final = graph.get_state(config)
    assert final.values["layer_status"]["bronze"] == "done"
