"""Silver node â€” clean and conform the bronze table into a silver table."""

from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from typing import Any

from de_agent.agent.nodes.notebook_generation import build_layer
from de_agent.agent.state import Layer, StageStatus
from de_agent.domain.plan import ExecutionPlan, LayerSpec


def silver_node(state: dict[str, Any], config: RunnableConfig) -> dict[str, Any]:
    plan = ExecutionPlan(**state["execution_plan"])
    spec = plan.spec_for(Layer.SILVER.value) or LayerSpec(
        layer=Layer.SILVER.value, objective="Clean and conform"
    )
    catalog, schema = state["catalog"], state["schema_name"]
    bronze_table = state["tables_by_layer"].get(Layer.BRONZE.value, "")
    target = f"{catalog}.{schema}.{spec.target_table or 'silver_' + plan.dataset_name}"

    update: dict[str, Any] = {
        "current_layer": Layer.SILVER.value,
        "layer_status": {**state["layer_status"], Layer.SILVER.value: StageStatus.IN_PROGRESS.value},
    }
    result = build_layer(
        {**state, **update},
        config,
        layer=Layer.SILVER.value,
        source_table=bronze_table,
        target_table=target,
        spec=spec,
    )
    return {**update, **result}
