"""Gold build node â€” materialize the curated dimensional layer via the shared loop."""

from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from typing import Any

from de_agent.agent.nodes.notebook_generation import build_layer
from de_agent.agent.state import Layer, StageStatus
from de_agent.domain.plan import ExecutionPlan, LayerSpec


def gold_build_node(state: dict[str, Any], config: RunnableConfig) -> dict[str, Any]:
    plan = ExecutionPlan(**state["execution_plan"])
    spec = plan.spec_for(Layer.GOLD.value) or LayerSpec(
        layer=Layer.GOLD.value, objective="Materialize the Gold star schema"
    )
    catalog, schema = state["catalog"], state["schema_name"]
    silver_table = state["tables_by_layer"].get(Layer.SILVER.value, "")
    target = f"{catalog}.{schema}.{spec.target_table or 'gold_' + plan.dataset_name}"

    update: dict[str, Any] = {
        "current_layer": Layer.GOLD.value,
        "layer_status": {**state["layer_status"], Layer.GOLD.value: StageStatus.IN_PROGRESS.value},
    }
    result = build_layer(
        {**state, **update},
        config,
        layer=Layer.GOLD.value,
        source_table=silver_table,
        target_table=target,
        spec=spec,
    )
    return {**update, **result}
