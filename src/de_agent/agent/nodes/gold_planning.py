"""Gold planning node â€” turn the confirmed star schema into a build spec."""

from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from typing import Any

from de_agent.agent.nodes._helpers import ai
from de_agent.domain.plan import LayerSpec
from de_agent.domain.schema import StarSchema


def gold_planning_node(state: dict[str, Any], config: RunnableConfig) -> dict[str, Any]:
    star = StarSchema(**state["gold_design"])
    transformations = [f"build {f.name} (grain: {f.grain})" for f in star.facts]
    transformations += [f"build {d.name} (grain: {d.grain})" for d in star.dimensions]

    dataset = state["dataset"]["name"]
    spec = LayerSpec(
        layer="gold",
        objective="Materialize the dimensional (star-schema) Gold model",
        transformations=transformations,
        target_table=f"gold_{dataset}",
        dq_rules=["fact row_count > 0", "dimension keys unique"],
    )
    return {
        "execution_plan": {
            **state["execution_plan"],
            "layers": [*state["execution_plan"]["layers"], spec.model_dump()],
        },
        "messages": [ai(f"Gold plan ready: {len(star.facts)} fact(s), {len(star.dimensions)} dim(s).")],
    }
