"""Real Databricks service backed by the Databricks SDK + SQL connector.

Kept intentionally defensive and idempotent: provisioning checks existence first
and degrades to a clear, actionable error when the service principal lacks a
privilege (notably ``CREATE CATALOG`` on the metastore).
"""

from __future__ import annotations

import base64
import io
import time
from typing import TYPE_CHECKING

from de_agent.config.logging import get_logger
from de_agent.services.databricks.models import (
    ColumnInfo,
    ObjectResult,
    RunResult,
    TableInfo,
)

if TYPE_CHECKING:
    from de_agent.config.settings import Settings

log = get_logger(__name__)


class SdkDatabricksService:
    def __init__(self, settings: Settings) -> None:
        from databricks.sdk import WorkspaceClient

        self._settings = settings
        self._warehouse_id = settings.databricks.warehouse_id
        # On Databricks Apps, the service principal is picked up from the runtime.
        if settings.databricks.host and settings.databricks.token:
            self._w = WorkspaceClient(
                host=settings.databricks.host, token=settings.databricks.token
            )
        else:
            self._w = WorkspaceClient()

    # ── provisioning ──
    def ensure_catalog(self, name: str, *, allow_create: bool) -> ObjectResult:
        try:
            self._w.catalogs.get(name)
            return ObjectResult(name=name, created=False, already_existed=True)
        except Exception:  # noqa: BLE001 - SDK raises NotFound; treat as "missing"
            pass
        if not allow_create:
            return ObjectResult(
                name=name,
                created=False,
                error=(
                    f"Catalog '{name}' does not exist and ALLOW_CREATE_CATALOG is false. "
                    f"Ask an admin to pre-create it and grant the service principal "
                    f"USE CATALOG + CREATE SCHEMA, or enable ALLOW_CREATE_CATALOG."
                ),
            )
        try:
            self._w.catalogs.create(name=name)
            return ObjectResult(name=name, created=True)
        except Exception as exc:  # noqa: BLE001
            return ObjectResult(
                name=name,
                created=False,
                error=(
                    f"Failed to create catalog '{name}': {exc}. The service principal "
                    f"likely lacks CREATE CATALOG on the metastore."
                ),
            )

    def ensure_schema(self, catalog: str, schema: str) -> ObjectResult:
        return self._ensure_sql(
            f"CREATE SCHEMA IF NOT EXISTS `{catalog}`.`{schema}`", f"{catalog}.{schema}"
        )

    def ensure_volume(self, catalog: str, schema: str, volume: str) -> ObjectResult:
        return self._ensure_sql(
            f"CREATE VOLUME IF NOT EXISTS `{catalog}`.`{schema}`.`{volume}`",
            f"{catalog}.{schema}.{volume}",
        )

    def _ensure_sql(self, sql: str, fq: str) -> ObjectResult:
        result = self.run_sql(sql)
        if result.success:
            return ObjectResult(name=fq, created=True)
        return ObjectResult(name=fq, created=False, error=result.error)

    def upload_dataset(
        self, *, catalog: str, schema: str, volume: str, filename: str, data: bytes
    ) -> str:
        path = f"/Volumes/{catalog}/{schema}/{volume}/{filename}"
        self._w.files.upload(path, io.BytesIO(data), overwrite=True)
        log.info("upload_dataset", path=path, bytes=len(data))
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
        fq = f"`{catalog}`.`{schema}`.`{table}`"
        sql = (
            f"CREATE TABLE IF NOT EXISTS {fq} AS "
            f"SELECT * FROM read_files('{volume_file_path}', format => '{file_format}', "
            f"header => true, inferSchema => true)"
        )
        result = self.run_sql(sql)
        if result.success:
            return ObjectResult(name=f"{catalog}.{schema}.{table}", created=True)
        return ObjectResult(name=f"{catalog}.{schema}.{table}", created=False, error=result.error)

    # ── execution ──
    def run_sql(self, sql: str) -> RunResult:
        from databricks.sdk.service.sql import StatementState

        started = time.monotonic()
        try:
            resp = self._w.statement_execution.execute_statement(
                warehouse_id=self._warehouse_id, statement=sql, wait_timeout="50s"
            )
            status = resp.status
            state = status.state if status else None
            if state == StatementState.SUCCEEDED:
                affected = 0
                if resp.result and resp.result.row_count:
                    affected = int(resp.result.row_count)
                return RunResult(
                    success=True,
                    statement_id=resp.statement_id,
                    rows_affected=affected,
                    duration_s=round(time.monotonic() - started, 3),
                )
            error_msg = status.error.message if status and status.error else "unknown SQL error"
            error_cls = (
                status.error.error_code.value
                if status and status.error and status.error.error_code
                else None
            )
            return RunResult(
                success=False,
                statement_id=resp.statement_id,
                error=error_msg,
                error_class=error_cls,
                duration_s=round(time.monotonic() - started, 3),
            )
        except Exception as exc:  # noqa: BLE001
            return RunResult(
                success=False,
                error=str(exc),
                error_class=type(exc).__name__,
                duration_s=round(time.monotonic() - started, 3),
            )

    def create_notebook(self, *, path: str, cells: list[str]) -> str:
        from databricks.sdk.service.workspace import ImportFormat, Language

        source = "\n\n-- COMMAND ----------\n\n".join(cells)
        content = base64.b64encode(source.encode("utf-8")).decode("utf-8")
        self._w.workspace.import_(
            path=path,
            content=content,
            format=ImportFormat.SOURCE,
            language=Language.SQL,
            overwrite=True,
        )
        return path

    # ── introspection ──
    def get_table_info(self, fq_table: str) -> TableInfo:
        count_result = self.run_sql(f"SELECT COUNT(*) AS n FROM {fq_table}")
        row_count = count_result.rows_affected if count_result.success else 0
        columns: list[ColumnInfo] = []
        try:
            parts = fq_table.replace("`", "").split(".")
            if len(parts) == 3:
                tbl = self._w.tables.get(full_name=fq_table.replace("`", ""))
                columns = [
                    ColumnInfo(name=c.name or "", dtype=str(c.type_text or ""))
                    for c in (tbl.columns or [])
                ]
        except Exception:  # noqa: BLE001
            pass
        return TableInfo(fq_name=fq_table, row_count=row_count, columns=columns)
