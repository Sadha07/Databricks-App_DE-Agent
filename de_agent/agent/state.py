"""LangGraph state schema.

The state is the single source of truth for a run and is what the Postgres
checkpointer persists. Nodes return partial dict updates; the UI reads the state
to render progress and to know what a human is being asked to approve.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages


class Layer(str, Enum):
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"


class StageStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"
    FAILED = "failed"


class PendingArtifact(TypedDict, total=False):
    """A generated SQL artifact awaiting human approval."""

    layer: str
    sql: str
    notebook_path: str
    rationale: str


class AgentState(TypedDict, total=False):
    # Conversation (reducer appends messages)
    messages: Annotated[list[Any], add_messages]

    # Inputs
    business_instruction: str
    dataset: dict[str, Any]  # serialized DatasetRef
    raw_bytes_b64: str  # uploaded file, base64 (kept small; dummy datasets)

    # Provisioned scope (set by environment_setup)
    catalog: str
    schema_name: str
    landing_table: str

    # Derived
    profile: dict[str, Any]  # serialized DatasetProfile
    execution_plan: dict[str, Any]  # serialized ExecutionPlan
    gold_design: dict[str, Any]  # serialized StarSchema

    # Progress
    current_layer: str
    layer_status: dict[str, str]  # {"bronze": "done", ...}
    tables_by_layer: dict[str, str]
    sql_by_layer: dict[str, str]

    # HITL / control
    pending_artifact: PendingArtifact
    retry_count: dict[str, int]
    validation: dict[str, Any]
    errors: list[dict[str, Any]]

    # Run identity + runtime options
    run_id: str
    require_approval: bool
    gold_instructions_given: bool


def new_state(
    *,
    run_id: str,
    business_instruction: str,
    dataset: dict[str, Any],
    raw_bytes_b64: str,
    require_approval: bool,
) -> AgentState:
    return AgentState(
        messages=[],
        business_instruction=business_instruction,
        dataset=dataset,
        raw_bytes_b64=raw_bytes_b64,
        current_layer=Layer.BRONZE.value,
        layer_status={layer.value: StageStatus.PENDING.value for layer in Layer},
        tables_by_layer={},
        sql_by_layer={},
        retry_count={},
        errors=[],
        run_id=run_id,
        require_approval=require_approval,
        gold_instructions_given=bool(business_instruction.strip()),
    )
