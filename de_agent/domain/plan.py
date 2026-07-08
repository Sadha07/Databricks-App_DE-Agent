"""Execution plan domain models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LayerSpec(BaseModel):
    """Per-layer intent produced by the planning agent."""

    layer: str  # bronze | silver | gold
    objective: str
    transformations: list[str] = Field(default_factory=list)
    target_table: str = ""
    dq_rules: list[str] = Field(default_factory=list)


class ExecutionPlan(BaseModel):
    catalog: str
    schema_name: str
    dataset_name: str
    layers: list[LayerSpec] = Field(default_factory=list)

    def spec_for(self, layer: str) -> LayerSpec | None:
        return next((s for s in self.layers if s.layer == layer), None)
