"""Generate human-readable pipeline documentation from the final run state."""

from __future__ import annotations

from de_agent.domain.plan import ExecutionPlan
from de_agent.domain.schema import StarSchema


class DocumentationBuilder:
    def build(
        self,
        *,
        plan: ExecutionPlan,
        star_schema: StarSchema | None,
        tables_by_layer: dict[str, str],
    ) -> str:
        lines = [
            f"# {plan.dataset_name} — Medallion pipeline",
            "",
            f"**Catalog:** `{plan.catalog}`  **Schema:** `{plan.schema_name}`",
            "",
            "## Layers",
        ]
        for layer in ("bronze", "silver", "gold"):
            spec = plan.spec_for(layer)
            table = tables_by_layer.get(layer, "—")
            lines.append(f"\n### {layer.title()} → `{table}`")
            if spec:
                lines.append(f"{spec.objective}")
                if spec.transformations:
                    lines.append("\nTransformations:")
                    lines.extend(f"- {t}" for t in spec.transformations)
        if star_schema:
            lines.append("\n## Gold star schema\n")
            lines.append("```\n" + star_schema.describe() + "\n```")
        return "\n".join(lines)
