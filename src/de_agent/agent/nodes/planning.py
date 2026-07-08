"""Planning node â€” generate the Bronze/Silver execution plan."""

from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from typing import Any

from de_agent.agent.nodes._helpers import ai, extract_json, record_error, system_for
from de_agent.config.logging import get_logger
from de_agent.domain.dataset import DatasetProfile
from de_agent.domain.plan import ExecutionPlan, LayerSpec
from de_agent.services.container import get_container

log = get_logger(__name__)


def planning_node(state: dict[str, Any], config: RunnableConfig) -> dict[str, Any]:
    container = get_container(config)
    llm = container.llm.for_node("planning")

    profile = DatasetProfile(**state["profile"])
    prompt = (
        f"Dataset profile:\n{profile.summary()}\n\n"
        f"Business instruction: {state.get('business_instruction') or '(none)'}\n\n"
        "Produce the Bronze and Silver execution plan."
    )

    try:
        raw = extract_json(llm.complete(system=system_for("planning"), prompt=prompt).text)
        layers = [LayerSpec(**spec) for spec in raw.get("layers", [])]
    except Exception as exc:  # noqa: BLE001
        return {
            "errors": record_error(state, node="planning", message=str(exc)),
            "messages": [ai(f"Planning failed: {exc}")],
        }

    plan = ExecutionPlan(
        catalog=state["catalog"],
        schema_name=state["schema_name"],
        dataset_name=state["dataset"]["name"],
        layers=layers,
    )
    log.info("planning.done", layers=[layer.layer for layer in layers])
    summary = "; ".join(f"{layer.layer}: {layer.objective}" for layer in layers)
    return {
        "execution_plan": plan.model_dump(),
        "messages": [ai(f"Execution plan ready â€” {summary}")],
    }
