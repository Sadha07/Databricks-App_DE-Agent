"""Unit tests for the service layer using fakes/real-local implementations."""

from __future__ import annotations

from de_agent.services.databricks.fake import InMemoryDatabricksService
from de_agent.services.llm.fake import FakeLLMClient
from de_agent.services.profiling import DatasetProfiler
from de_agent.services.validation import LayerValidator


def test_profiler_detects_key_and_nulls(dummy_csv_bytes: bytes) -> None:
    profile = DatasetProfiler().profile_csv_bytes(dummy_csv_bytes)
    assert profile.row_count == 8
    assert profile.column_count == 6
    order_id = profile.column("order_id")
    amount = profile.column("amount")
    assert order_id is not None and order_id.is_candidate_key
    assert amount is not None and amount.null_count == 1


def test_fake_databricks_creates_table_on_ctas() -> None:
    db = InMemoryDatabricksService()
    result = db.run_sql("CREATE OR REPLACE TABLE cat.sch.silver AS SELECT 1")
    assert result.success
    assert db.get_table_info("cat.sch.silver").row_count > 0


def test_fake_databricks_can_force_failure() -> None:
    db = InMemoryDatabricksService()
    db.fail_next_sql = "boom"
    assert not db.run_sql("CREATE TABLE x AS SELECT 1").success
    assert db.run_sql("CREATE TABLE x AS SELECT 1").success  # only next call fails


def test_validator_passes_for_existing_table() -> None:
    db = InMemoryDatabricksService()
    db.run_sql("CREATE TABLE cat.sch.t AS SELECT 1")
    result = LayerValidator(db).validate(fq_table="cat.sch.t", min_rows=1)
    assert result.passed


def test_fake_llm_routes_on_task_marker() -> None:
    llm = FakeLLMClient()
    plan = llm.complete(system="TASK: planning\n...", prompt="x").text
    sql = llm.complete(
        system="TASK: sql_generation\n...",
        prompt="Target table (fully qualified): cat.sch.silver\nSource table: cat.sch.bronze",
    ).text
    assert '"layers"' in plan
    assert "CREATE OR REPLACE TABLE cat.sch.silver" in sql
