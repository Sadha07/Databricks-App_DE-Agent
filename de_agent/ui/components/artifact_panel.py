"""Artifact / review panel — renders the current HITL gate and resumes the graph.

Handles the three interrupt types: SQL approval (approve / edit / reject with
feedback), clarification (free-text answer), and Gold confirmation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import streamlit as st

from de_agent.ui import state_bridge

if TYPE_CHECKING:
    from de_agent.config.settings import Settings


def render_artifact_panel(
    settings: Settings, thread_id: str, interrupt: dict[str, Any] | None, state: dict[str, Any]
) -> None:
    st.subheader("Review")
    if interrupt is None:
        _render_idle(settings, thread_id, state)
        return

    kind = interrupt.get("type")
    if kind == "approval":
        _render_approval(settings, thread_id, interrupt)
    elif kind == "clarification":
        _render_text_gate(settings, thread_id, interrupt, key="clarify")
    elif kind == "gold_confirmation":
        _render_text_gate(settings, thread_id, interrupt, key="gold")
    else:
        st.warning(f"Waiting on: {kind}")


def _render_idle(settings: Settings, thread_id: str, state: dict[str, Any]) -> None:
    if state_bridge.is_done(settings, thread_id):
        st.success("Run complete.")
    else:
        st.info("Working…")
    sql_by_layer = state.get("sql_by_layer", {})
    for layer, sql in sql_by_layer.items():
        with st.expander(f"{layer.title()} SQL"):
            st.code(sql, language="sql")


def _render_approval(settings: Settings, thread_id: str, interrupt: dict[str, Any]) -> None:
    layer = interrupt.get("layer", "")
    st.markdown(f"**{layer.title()} notebook** — awaiting approval")
    st.caption(interrupt.get("rationale", ""))
    edited = st.text_area("SQL", value=interrupt.get("sql", ""), height=220, key=f"sql_{layer}")

    col_a, col_b, col_c = st.columns(3)
    if col_a.button("Approve & run", type="primary", key=f"approve_{layer}"):
        original = interrupt.get("sql", "")
        action = {"action": "edit", "sql": edited} if edited != original else {"action": "approve"}
        state_bridge.resume_run(settings, thread_id, action)
        st.rerun()
    if col_b.button("Reject", key=f"reject_{layer}"):
        st.session_state[f"show_feedback_{layer}"] = True
    if col_c.button("Refresh", key=f"refresh_{layer}"):
        st.rerun()

    if st.session_state.get(f"show_feedback_{layer}"):
        feedback = st.text_input("What should change?", key=f"fb_{layer}")
        if st.button("Send feedback", key=f"send_fb_{layer}") and feedback:
            state_bridge.resume_run(settings, thread_id, {"action": "reject", "feedback": feedback})
            st.session_state.pop(f"show_feedback_{layer}", None)
            st.rerun()


def _render_text_gate(
    settings: Settings, thread_id: str, interrupt: dict[str, Any], *, key: str
) -> None:
    st.markdown(interrupt.get("question", ""))
    answer = st.text_input("Your response", key=f"answer_{key}")
    if st.button("Submit", type="primary", key=f"submit_{key}") and answer:
        state_bridge.resume_run(settings, thread_id, answer)
        st.rerun()
