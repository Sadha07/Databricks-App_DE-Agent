"""Clarification node â€” decide whether the request needs a human answer."""

from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from typing import Any

from langchain_core.messages import HumanMessage
from langgraph.types import interrupt

from de_agent.agent.nodes._helpers import ai, extract_json, system_for
from de_agent.config.logging import get_logger
from de_agent.services.container import get_container

log = get_logger(__name__)


def clarification_node(state: dict[str, Any], config: RunnableConfig) -> dict[str, Any]:
    container = get_container(config)
    llm = container.llm.for_node("clarification")

    dataset = state.get("dataset", {})
    instruction = state.get("business_instruction", "") or "(none provided)"
    prompt = (
        f"Dataset: {dataset.get('name', 'unknown')} (file {dataset.get('source_filename', '?')})\n"
        f"Business instruction: {instruction}\n\n"
        "Decide if clarification is required."
    )

    try:
        decision = extract_json(llm.complete(system=system_for("clarification"), prompt=prompt).text)
    except Exception as exc:  # noqa: BLE001 â€” never block a run on a parse hiccup
        log.warning("clarification.parse_failed", error=str(exc))
        return {"messages": [ai("Proceeding without clarification.")]}

    if not decision.get("needs_clarification"):
        return {"messages": [ai("Understood the request. Setting up the environment.")]}

    question = decision.get("question", "Could you clarify the pipeline goal?")
    # Pause the graph; the UI renders the question and resumes with the answer.
    answer = interrupt({"type": "clarification", "question": question})
    return {
        "messages": [ai(question), HumanMessage(content=str(answer))],
        "business_instruction": f"{state.get('business_instruction', '')}\n{answer}".strip(),
    }
