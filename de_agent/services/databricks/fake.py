"""In-memory Databricks service.

Simulates UC provisioning and SQL execution so the entire graph — including the
generate/execute/validate/retry loops and HITL gates — runs locally with no cloud
access. Used by ``DE_AGENT_ENV=local`` and by the test suite.
"""

from __future__ import annotations

import re

from de_agent.config.logging import get_logger
from de_agent.services.databricks.models import (
    ColumnInfo,
    ObjectResult,
    RunResult,
    TableInfo,
)

log = get_logger(__name__)

_CREATE_TABLE_RE = re.compile(
    r"create\s+(or\s+replace\s+)?table\s+([a-zA-Z0-9_.`]+)", re.IGNORECASE
)


class InMemoryDatabricksService:
    """Deterministic fake. Records all operations; tables 'succeed' by default."""

    def __init__(self, default_row_count: int = 100) -> None:
        self._default_row_count = default_row_count
        self.catalogs: set[str] = set()
        self.schemas: set[str] = set()
        self.volumes: set[str] = set()
        self.tables: dict[str, TableInfo] = {}
        self.notebooks: dict[str, list[str]] = {}
        self.executed_sql: list[str] = []
        # Optional hook for tests to force the next run_sql to fail.
        self.fail_next_sql: str | None = None

    # ── provisioning ──
    def ensure_catalog(self, name: str, *, allow_create: bool) -> ObjectResult:
        if name in self.catalogs:
            return ObjectResult(name=name, created=False, already_existed=True)
        if not allow_create:
            # Simulate the common prod case: catalog must be pre-created.
            self.catalogs.add(name)  # assume it exists in the fake
            return ObjectResult(name=name, created=False, already_existed=True)
        self.catalogs.add(name)
        return ObjectResult(name=name, created=True)

    def ensure_schema(self, catalog: str, schema: str) -> ObjectResult:
        fq = f"{catalog}.{schema}"
        created = fq not in self.schemas
        self.schemas.add(fq)
        return ObjectResult(name=fq, created=created, already_existed=not created)

    def ensure_volume(self, catalog: str, schema: str, volume: str) -> ObjectResult:
        fq = f"{catalog}.{schema}.{volume}"
        created = fq not in self.volumes
        self.volumes.add(fq)
        return ObjectResult(name=fq, created=created, already_existed=not created)

    def upload_dataset(
        self, *, catalog: str, schema: str, volume: str, filename: str, data: bytes
    ) -> str:
        path = f"/Volumes/{catalog}/{schema}/{volume}/{filename}"
        log.info("fake.upload_dataset", path=path, bytes=len(data))
        return path

    def register_bronze_table(
        self,
        *,
        catalog: str,
        schema: str,
        table: str,
        volume_file_path: str,
        file_format: str = "csv",
    ) -> ObjectResult:
        fq = f"{catalog}.{schema}.{table}"
        self.tables[fq] = TableInfo(fq_name=fq, row_count=self._default_row_count)
        return ObjectResult(name=fq, created=True)

    # ── execution ──
    def run_sql(self, sql: str) -> RunResult:
        self.executed_sql.append(sql)
        if self.fail_next_sql is not None:
            err = self.fail_next_sql
            self.fail_next_sql = None
            return RunResult(success=False, error=err, error_class="SIMULATED")

        for match in _CREATE_TABLE_RE.finditer(sql):
            fq = match.group(2).replace("`", "")
            self.tables[fq] = TableInfo(
                fq_name=fq,
                row_count=self._default_row_count,
                columns=[ColumnInfo(name="col_1", dtype="string")],
            )
        return RunResult(success=True, statement_id="fake-stmt", rows_affected=self._default_row_count)

    def create_notebook(self, *, path: str, cells: list[str]) -> str:
        self.notebooks[path] = cells
        return path

    def get_table_info(self, fq_table: str) -> TableInfo:
        return self.tables.get(fq_table, TableInfo(fq_name=fq_table, row_count=0))
