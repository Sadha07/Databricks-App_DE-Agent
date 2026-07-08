"""Finalize node — documentation, lineage, manifest, and versioned artifacts."""

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
    db = container.databricks
    plan = ExecutionPlan(**state["execution_plan"])
    star = StarSchema(**state["gold_design"]) if state.get("gold_design") else None
    tables = state.get("tables_by_layer", {})
    sql_by_layer = state.get("sql_by_layer", {})
    run_id = state["run_id"]

    documentation = container.documentation.build(
        plan=plan, star_schema=star, tables_by_layer=tables
    )
    lineage = container.lineage.build(
        tables_by_layer=tables, source=state.get("landing_table", "source")
    )
    manifest = RunManifest(
        run_id=run_id,
        dataset=plan.dataset_name,
        catalog=plan.catalog,
        schema_name=plan.schema_name,
        tables_by_layer=tables,
        sql_by_layer=sql_by_layer,
    )
    location = container.artifacts.save(
        manifest, documentation=documentation, lineage_mermaid=lineage.to_mermaid()
    )

    # ── Publish notebooks to Databricks Workspace ──────────────────────────────
    # One SQL notebook per layer so the user can find and run them directly.
    workspace_folder = f"/Shared/de_agent/{run_id}"
    notebook_paths: list[str] = []
    for layer, sql in sql_by_layer.items():
        if sql:
            try:
                nb_path = db.create_notebook(
                    path=f"{workspace_folder}/{layer}", cells=[sql]
                )
                notebook_paths.append(nb_path)
                log.info("finalize.notebook_created", layer=layer, path=nb_path)
            except Exception as exc:  # noqa: BLE001
                log.warning("finalize.notebook_failed", layer=layer, error=str(exc))

    # Summary markdown notebook (documentation + lineage as comments)
    if documentation:
        summary_sql = (
            "-- Pipeline Summary\n"
            "-- ─────────────────────────────────────────────\n"
            + "\n".join(f"-- {line}" for line in documentation.splitlines())
            + "\n\n-- Lineage\n"
            + "\n".join(f"-- {line}" for line in lineage.to_mermaid().splitlines())
        )
        try:
            db.create_notebook(path=f"{workspace_folder}/_summary", cells=[summary_sql])
        except Exception as exc:  # noqa: BLE001
            log.warning("finalize.summary_notebook_failed", error=str(exc))

    nb_count = len(notebook_paths)
    log.info("finalize.done", location=location, notebooks=nb_count)

    notebook_note = (
        f" Notebooks published to `{workspace_folder}` ({nb_count} layer(s))."
        if notebook_paths
        else ""
    )
    return {
        "messages": [
            ai(
                f"Pipeline complete. Artifacts saved to `{location}`."
                f"{notebook_note}"
            )
        ],
    }

