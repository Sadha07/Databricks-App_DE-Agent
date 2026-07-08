"""Bronze node â€” raw ingest from the landing table into a bronze table."""

from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from typing import Any

from de_agent.agent.nodes.notebook_generation import build_layer
from de_agent.agent.state import Layer, StageStatus
from de_agent.domain.plan import ExecutionPlan, LayerSpec


def bronze_node(state: dict[str, Any], config: RunnableConfig) -> dict[str, Any]:
    plan = ExecutionPlan(**state["execution_plan"])
    spec = plan.spec_for(Layer.BRONZE.value) or LayerSpec(
        layer=Layer.BRONZE.value, objective="Ingest raw data as-is"
    )
    catalog, schema = state["catalog"], state["schema_name"]
    target = f"{catalog}.{schema}.{spec.target_table or 'bronze_' + plan.dataset_name}"

    update: dict[str, Any] = {
        "current_layer": Layer.BRONZE.value,
        "layer_status": {**state["layer_status"], Layer.BRONZE.value: StageStatus.IN_PROGRESS.value},
    }
    result = build_layer(
        {**state, **update},
        config,
        layer=Layer.BRONZE.value,
        source_table=state["landing_table"],
        target_table=target,
        spec=spec,
    )
    return {**update, **result}
