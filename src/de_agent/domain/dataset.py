"""Dataset domain models — pure data, no I/O."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DatasetRef(BaseModel):
    """A pointer to an ingested dataset in Unity Catalog."""

    name: str
    source_filename: str
    volume_path: str = ""
    bronze_table: str = ""
    row_count: int = 0


class ColumnProfile(BaseModel):
    name: str
    dtype: str
    null_count: int = 0
    null_fraction: float = 0.0
    distinct_count: int = 0
    sample_values: list[str] = Field(default_factory=list)
    is_candidate_key: bool = False


class DatasetProfile(BaseModel):
    row_count: int
    column_count: int
    columns: list[ColumnProfile] = Field(default_factory=list)

    def column(self, name: str) -> ColumnProfile | None:
        return next((c for c in self.columns if c.name == name), None)

    def summary(self) -> str:
        lines = [f"{self.row_count} rows, {self.column_count} columns"]
        for c in self.columns:
            key = " (candidate key)" if c.is_candidate_key else ""
            lines.append(f"  - {c.name}: {c.dtype}, {c.null_fraction:.0%} null{key}")
        return "\n".join(lines)
