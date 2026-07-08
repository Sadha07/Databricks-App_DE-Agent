"""Shared layer build loop.

One reusable routine that generates SQL, optionally gates on human approval via
``interrupt()``, executes, validates, and self-corrects by feeding errors/validation
failures back to the LLM â€” capped by ``max_retries`` so it can never loop forever.

Bronze, Silver, and Gold-build nodes all delegate here; only the source/target/intent
differ. Keeping execution strictly *after* the approval interrupt means a resume never
re-executes SQL.
"""

from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from typing import Any

from langgraph.types import interrupt

from de_agent.agent.nodes._helpers import (
    ai,
    bump_retry,
    extract_sql,
    record_error,
    system_for,
)
from de_agent.agent.state import StageStatus
from de_agent.config.logging import get_logger
from de_agent.domain.plan import LayerSpec
from de_agent.services.container import AppContainer, get_container

log = get_logger(__name__)


def _generate_sql(
    container: AppContainer,
    *,
    layer: str,
    source_table: str,
    target_table: str,
    spec: LayerSpec,
    profile_summary: str,
) -> str:
    llm = container.llm.for_node("sql_generation")
    prompt = (
        f"Layer: {layer}\n"
        f"Source table: {source_table}\n"
        f"Target table (fully qualified): {target_table}\n"
        f"Objective: {spec.objective}\n"
        f"Transformations: {', '.join(spec.transformations) or 'none'}\n"
        f"DQ rules: {', '.join(spec.dq_rules) or 'none'}\n\n"
        f"Source profile:\n{profile_summary}\n\n"
        "Generate the CREATE OR REPLACE TABLE statement."
    )
    return extract_sql(llm.complete(system=system_for("sql_generation"), prompt=prompt).text)


def _correct_sql(container: AppContainer, *, previous_sql: str, failure: str, layer: str) -> str:
    llm = container.llm.for_node("sql_generation")
    prompt = (
        f"Layer: {layer}\nPrevious SQL:\n{previous_sql}\n\n"
        f"Failure to fix:\n{failure}\n\nReturn corrected SQL."
    )
    return extract_sql(llm.complete(system=system_for("error_correction"), prompt=prompt).text)


def build_layer(
    state: dict[str, Any],
    config: RunnableConfig,
    *,
    layer: str,
    source_table: str,
    target_table: str,
    spec: LayerSpec,
) -> dict[str, Any]:
    container = get_container(config)
    db = container.databricks
    max_retries = container.settings.max_retries
    profile_summary = _summarize_profile(state)

    sql = _generate_sql(
        container,
        layer=layer,
        source_table=source_table,
        target_table=target_table,
        spec=spec,
        profile_summary=profile_summary,
    )

    # â”€â”€ Human approval gate (before any execution, so resume never double-runs SQL) â”€â”€
    if state.get("require_approval"):
        while True:
            decision = interrupt(
                {
                    "type": "approval",
                    "layer": layer,
                    "sql": sql,
                    "target_table": target_table,
                    "rationale": spec.objective,
                }
            )
            action = (decision or {}).get("action", "approve")
            if action == "approve":
                break
            if action == "edit":
                sql = extract_sql(decision.get("sql", sql))
                break
            # reject â†’ regenerate with feedback, ask again
            sql = _correct_sql(
                container, previous_sql=sql, failure=decision.get("feedback", "rejected"), layer=layer
            )

    # â”€â”€ Execute + self-correct on SQL errors â”€â”€
    run = db.run_sql(sql)
    attempts = 0
    while not run.success and attempts < max_retries:
        attempts += 1
        log.warning("build.sql_error", layer=layer, attempt=attempts, error=run.error)
        sql = _correct_sql(container, previous_sql=sql, failure=run.error or "", layer=layer)
        run = db.run_sql(sql)

    if not run.success:
        return _fail(state, layer, f"SQL failed after {attempts} retries: {run.error}")

    # â”€â”€ Validate + self-correct on unexpected output â”€â”€
    validation = container.validator.validate(fq_table=target_table, min_rows=1)
    vattempts = 0
    while not validation.passed and vattempts < max_retries:
        vattempts += 1
        log.warning("build.validation_failed", layer=layer, attempt=vattempts)
        sql = _correct_sql(
            container, previous_sql=sql, failure=validation.summary(), layer=layer
        )
        run = db.run_sql(sql)
        if not run.success:
            return _fail(state, layer, f"SQL failed during validation retry: {run.error}")
        validation = container.validator.validate(fq_table=target_table, min_rows=1)

    if not validation.passed:
        return _fail(state, layer, f"Validation failed:\n{validation.summary()}")

    notebook_path = db.create_notebook(
        path=f"/Shared/de_agent/{state['run_id']}/{layer}", cells=[sql]
    )
    # DDL statements (CREATE OR REPLACE TABLE AS SELECT) do not return a row count
    # from the Databricks SQL API. Query the real count from the materialised table.
    try:
        real_row_count = db.get_table_info(target_table).row_count
    except Exception:  # noqa: BLE001
        real_row_count = run.rows_affected
    log.info("build.done", layer=layer, table=target_table, notebook=notebook_path, rows=real_row_count)
    return {
        "sql_by_layer": {**state.get("sql_by_layer", {}), layer: sql},
        "tables_by_layer": {**state.get("tables_by_layer", {}), layer: target_table},
        "layer_status": {**state["layer_status"], layer: StageStatus.DONE.value},
        "validation": validation.model_dump(),
        "pending_artifact": {},
        "messages": [ai(f"{layer.title()} complete â†’ `{target_table}` ({real_row_count:,} rows).")],
    }


def _summarize_profile(state: dict[str, Any]) -> str:
    from de_agent.domain.dataset import DatasetProfile

    profile = state.get("profile")
    return DatasetProfile(**profile).summary() if profile else "(no profile)"


def _fail(state: dict[str, Any], layer: str, message: str) -> dict[str, Any]:
    return {
        "errors": record_error(state, node=f"{layer}_build", message=message),
        "retry_count": bump_retry(state, layer),
        "layer_status": {**state["layer_status"], layer: StageStatus.FAILED.value},
        "messages": [ai(f"{layer.title()} failed: {message}")],
    }
