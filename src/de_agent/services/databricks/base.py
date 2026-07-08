"""Databricks capability interface.

Nodes depend on this Protocol, never on the SDK directly. Two implementations
exist: ``SdkDatabricksService`` (real) and ``InMemoryDatabricksService`` (fake,
for local dev and tests).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from de_agent.services.databricks.models import ObjectResult, RunResult, TableInfo


@runtime_checkable
class DatabricksService(Protocol):
    # ── Unity Catalog provisioning ──
    def ensure_catalog(self, name: str, *, allow_create: bool) -> ObjectResult: ...

    def ensure_schema(self, catalog: str, schema: str) -> ObjectResult: ...

    def ensure_volume(self, catalog: str, schema: str, volume: str) -> ObjectResult: ...

    def upload_dataset(
        self, *, catalog: str, schema: str, volume: str, filename: str, data: bytes
    ) -> str:
        """Upload raw bytes to a UC volume; returns the full volume file path."""
        ...

    def register_bronze_table(
        self,
        *,
        catalog: str,
        schema: str,
        table: str,
        volume_file_path: str,
        file_format: str = "csv",
    ) -> ObjectResult: ...

    # ── Execution ──
    def run_sql(self, sql: str) -> RunResult: ...

    def create_notebook(self, *, path: str, cells: list[str]) -> str:
        """Create/overwrite a notebook from SQL cells; returns the workspace path."""
        ...

    # ── Introspection (used by validators) ──
    def get_table_info(self, fq_table: str) -> TableInfo: ...
