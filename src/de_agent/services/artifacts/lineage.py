"""Lineage assembly — captures the source→bronze→silver→gold table graph."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LineageEdge(BaseModel):
    source: str
    target: str
    layer: str


class Lineage(BaseModel):
    edges: list[LineageEdge] = Field(default_factory=list)

    def to_mermaid(self) -> str:
        lines = ["graph LR"]
        for e in self.edges:
            lines.append(f'  "{e.source}" --> "{e.target}"')
        return "\n".join(lines)


class LineageBuilder:
    def build(self, *, tables_by_layer: dict[str, str], source: str) -> Lineage:
        edges: list[LineageEdge] = []
        prev = source
        for layer in ("bronze", "silver", "gold"):
            target = tables_by_layer.get(layer)
            if target:
                edges.append(LineageEdge(source=prev, target=target, layer=layer))
                prev = target
        return Lineage(edges=edges)
