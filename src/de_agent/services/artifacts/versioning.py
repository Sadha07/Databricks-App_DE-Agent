"""Persist run artifacts: versioned SQL, notebooks, manifest, docs, lineage.

Locally writes to a scratch directory; on Databricks the same manifest can be
written to a UC volume. The manifest is the machine-readable record of a run.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field


class RunManifest(BaseModel):
    run_id: str
    dataset: str
    catalog: str
    schema_name: str
    tables_by_layer: dict[str, str] = Field(default_factory=dict)
    sql_by_layer: dict[str, str] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class ArtifactStore:
    def __init__(self, base_dir: str) -> None:
        self._base = Path(base_dir)

    def save(self, manifest: RunManifest, *, documentation: str, lineage_mermaid: str) -> str:
        run_dir = self._base / manifest.run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "manifest.json").write_text(manifest.model_dump_json(indent=2), "utf-8")
        (run_dir / "documentation.md").write_text(documentation, "utf-8")
        (run_dir / "lineage.mmd").write_text(lineage_mermaid, "utf-8")
        sql_dir = run_dir / "sql"
        sql_dir.mkdir(exist_ok=True)
        for layer, sql in manifest.sql_by_layer.items():
            (sql_dir / f"{layer}.sql").write_text(sql, "utf-8")
        return str(run_dir)

    @staticmethod
    def manifest_json(manifest: RunManifest) -> str:
        return json.dumps(manifest.model_dump(), indent=2)
