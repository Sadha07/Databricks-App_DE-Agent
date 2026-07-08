"""Finalize node â€” documentation, lineage, manifest, and versioned artifacts."""

from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from typing import Any

from de_agent.agent.nodes._helpers import ai
from de_agent.config.logging import get_logger
from de_agent.domain.plan import ExecutionPlan
from de_agent.domain.schema import StarSchema
from de_agent.services.artifacts.versioning import RunManifest
from de_agent.services.container import get_container

log = get_logger(__name__)


def finalize_node(state: dict[str, Any], config: RunnableConfig) -> dict[str, Any]:
    container = get_container(config)
    plan = ExecutionPlan(**state["execution_plan"])
    star = StarSchema(**state["gold_design"]) if state.get("gold_design") else None
    tables = state.get("tables_by_layer", {})

    documentation = container.documentation.build(
        plan=plan, star_schema=star, tables_by_layer=tables
    )
    lineage = container.lineage.build(
        tables_by_layer=tables, source=state.get("landing_table", "source")
    )
    manifest = RunManifest(
        run_id=state["run_id"],
        dataset=plan.dataset_name,
        catalog=plan.catalog,
        schema_name=plan.schema_name,
        tables_by_layer=tables,
        sql_by_layer=state.get("sql_by_layer", {}),
    )
    location = container.artifacts.save(
        manifest, documentation=documentation, lineage_mermaid=lineage.to_mermaid()
    )
    log.info("finalize.done", location=location)
    return {
        "messages": [ai(f"Pipeline complete. Artifacts saved to `{location}`.")],
    }
