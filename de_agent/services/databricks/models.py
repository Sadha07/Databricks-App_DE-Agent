"""Typed results returned by the Databricks service."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ObjectResult(BaseModel):
    """Result of ensuring a UC object (catalog/schema/volume/table) exists."""

    name: str
    created: bool
    already_existed: bool = False
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


class RunResult(BaseModel):
    """Result of executing SQL against a warehouse."""

    success: bool
    statement_id: str | None = None
    rows_affected: int = 0
    duration_s: float = 0.0
    error: str | None = None
    error_class: str | None = None


class ColumnInfo(BaseModel):
    name: str
    dtype: str


class TableInfo(BaseModel):
    fq_name: str
    row_count: int = 0
    columns: list[ColumnInfo] = Field(default_factory=list)
