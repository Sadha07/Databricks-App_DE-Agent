"""Gold reasoning node â€” interpret business meaning and design a star schema.

Corresponds to the flowchart's AI Interpretation/Reasoning + Gold Recommendation
Generator, followed by the Gold confirmation HITL gate.
"""

from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from typing import Any

from langchain_core.messages import HumanMessage
from langgraph.types import interrupt

from de_agent.agent.nodes._helpers import ai, extract_json, record_error, system_for
from de_agent.config.logging import get_logger
from de_agent.domain.dataset import DatasetProfile
from de_agent.domain.schema import Dimension, Fact, StarSchema
from de_agent.services.container import get_container

log = get_logger(__name__)


def gold_reasoning_node(state: dict[str, Any], config: RunnableConfig) -> dict[str, Any]:
    container = get_container(config)
    llm = container.llm.for_node("gold_reasoning")

    profile = DatasetProfile(**state["profile"]) if state.get("profile") else None
    silver_table = state["tables_by_layer"].get("silver", "")
    prompt = (
        f"Silver table: {silver_table}\n"
        f"Profile:\n{profile.summary() if profile else '(none)'}\n"
        f"Business context: {state.get('business_instruction') or '(none)'}\n\n"
        "Design the Gold star schema."
    )

    try:
        raw = extract_json(llm.complete(system=system_for("gold_reasoning"), prompt=prompt).text)
        star = StarSchema(
            facts=[Fact(**f) for f in raw.get("facts", [])],
            dimensions=[Dimension(**d) for d in raw.get("dimensions", [])],
            suggested_kpis=raw.get("suggested_kpis", []),
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "errors": record_error(state, node="gold_reasoning", message=str(exc)),
            "messages": [ai(f"Gold reasoning failed: {exc}")],
        }

    # â”€â”€ Gold confirmation gate â”€â”€
    if state.get("gold_instructions_given"):
        question = f"I'll build this Gold design:\n{star.describe()}\nProceed?"
    else:
        question = (
            "Which facts and dimensions do you want in Gold? Proposed:\n"
            f"{star.describe()}\nConfirm or adjust."
        )
    answer = interrupt({"type": "gold_confirmation", "question": question, "design": star.model_dump()})

    return {
        "gold_design": star.model_dump(),
        "messages": [ai(question), HumanMessage(content=str(answer))],
    }
