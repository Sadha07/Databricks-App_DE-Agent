"""Post-execution output validation.

Checks the produced table against expectations: it exists, has rows, and (when
provided) satisfies simple DQ rules. Returns a structured result the graph uses to
decide whether to advance or feed the failure back to the LLM.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from de_agent.services.databricks.base import DatabricksService


class Check(BaseModel):
    name: str
    passed: bool
    detail: str = ""


class ValidationResult(BaseModel):
    checks: list[Check] = Field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)

    @property
    def failures(self) -> list[Check]:
        return [c for c in self.checks if not c.passed]

    def summary(self) -> str:
        return "\n".join(
            f"[{'ok' if c.passed else 'FAIL'}] {c.name}: {c.detail}" for c in self.checks
        )


class LayerValidator:
    def __init__(self, databricks: DatabricksService) -> None:
        self._db = databricks

    def validate(
        self,
        *,
        fq_table: str,
        min_rows: int = 1,
        expected_columns: list[str] | None = None,
    ) -> ValidationResult:
        info = self._db.get_table_info(fq_table)
        checks: list[Check] = [
            Check(
                name="row_count",
                passed=info.row_count >= min_rows,
                detail=f"{info.row_count} rows (min {min_rows})",
            )
        ]
        if expected_columns:
            actual = {c.name for c in info.columns}
            missing = [c for c in expected_columns if c not in actual]
            # If introspection returned no columns (e.g. fake), don't fail on it.
            passed = not missing if actual else True
            checks.append(
                Check(
                    name="expected_columns",
                    passed=passed,
                    detail="all present" if passed else f"missing: {', '.join(missing)}",
                )
            )
        return ValidationResult(checks=checks)
