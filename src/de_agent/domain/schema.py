"""Star-schema domain models produced by the Gold reasoning/planning nodes."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Dimension(BaseModel):
    name: str
    grain: str
    attributes: list[str] = Field(default_factory=list)
    source_columns: list[str] = Field(default_factory=list)


class Fact(BaseModel):
    name: str
    grain: str
    measures: list[str] = Field(default_factory=list)
    dimension_keys: list[str] = Field(default_factory=list)


class StarSchema(BaseModel):
    facts: list[Fact] = Field(default_factory=list)
    dimensions: list[Dimension] = Field(default_factory=list)
    suggested_kpis: list[str] = Field(default_factory=list)

    def describe(self) -> str:
        facts = ", ".join(f.name for f in self.facts) or "none"
        dims = ", ".join(d.name for d in self.dimensions) or "none"
        return f"Facts: {facts}\nDimensions: {dims}\nKPIs: {', '.join(self.suggested_kpis)}"
