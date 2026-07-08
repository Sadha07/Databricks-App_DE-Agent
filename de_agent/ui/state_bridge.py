"""Bridge between Streamlit and the LangGraph runtime.

Streamlit re-runs its script top-to-bottom on every interaction, so the graph and
its checkpointer connection are cached as resources and live *outside* the run. The
graph is the source of truth: this module starts a run, resumes it after a human
decision, and surfaces the current state + any pending interrupt for rendering.
"""

from __future__ import annotations

import base64
import uuid
from typing import TYPE_CHECKING, Any

import streamlit as st
from langgraph.types import Command

from de_agent.agent.checkpointer import create_checkpointer
from de_agent.agent.graph import build_graph
from de_agent.agent.state import new_state
from de_agent.domain.dataset import DatasetRef
from de_agent.services.container import AppContainer

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph

    from de_agent.config.settings import Settings


@st.cache_resource
def _graph(_settings: Settings) -> CompiledStateGraph:
    return build_graph(create_checkpointer(_settings))


@st.cache_resource
def _container(_settings: Settings) -> AppContainer:
    return AppContainer(_settings)


def _config(settings: Settings, thread_id: str) -> dict[str, Any]:
    container = _container(settings)
    return {
        "configurable": {"thread_id": thread_id, **container.as_config_value()},
        "recursion_limit": 50,
    }


def start_run(
    settings: Settings,
    *,
    business_instruction: str,
    filename: str,
    data: bytes,
) -> str:
    thread_id = uuid.uuid4().hex
    dataset = DatasetRef(name=filename.rsplit(".", 1)[0], source_filename=filename)
    state = new_state(
        run_id=thread_id,
        business_instruction=business_instruction,
        dataset=dataset.model_dump(),
        raw_bytes_b64=base64.b64encode(data).decode("ascii"),
        require_approval=settings.require_approval,
    )
    _graph(settings).invoke(state, _config(settings, thread_id))
    return thread_id


def resume_run(settings: Settings, thread_id: str, value: Any) -> None:
    _graph(settings).invoke(Command(resume=value), _config(settings, thread_id))


def get_state(settings: Settings, thread_id: str) -> dict[str, Any]:
    snapshot = _graph(settings).get_state(_config(settings, thread_id))
    return dict(snapshot.values)


def pending_interrupt(settings: Settings, thread_id: str) -> dict[str, Any] | None:
    snapshot = _graph(settings).get_state(_config(settings, thread_id))
    for task in snapshot.tasks:
        if task.interrupts:
            value = task.interrupts[0].value
            return value if isinstance(value, dict) else {"type": "unknown", "value": value}
    return None


def is_done(settings: Settings, thread_id: str) -> bool:
    snapshot = _graph(settings).get_state(_config(settings, thread_id))
    return not snapshot.next
