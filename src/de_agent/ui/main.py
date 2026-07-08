"""Streamlit render loop — the 3-pane all-in-one app.

Layout: chat (left) · review/artifact panel (center) · stage tracker (right),
with dataset upload + run controls in the sidebar. All logic lives in the graph;
this module only reads state and dispatches human decisions back to it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import streamlit as st

from de_agent.ui import state_bridge
from de_agent.ui.components.artifact_panel import render_artifact_panel
from de_agent.ui.components.chat_panel import render_chat
from de_agent.ui.components.sidebar import render_sidebar
from de_agent.ui.components.stage_tracker import render_stage_tracker

if TYPE_CHECKING:
    from de_agent.config.settings import Settings


def render(settings: Settings) -> None:
    st.set_page_config(page_title="Databricks Medallion Agent", layout="wide")
    render_sidebar(settings)

    thread_id = st.session_state.get("thread_id")
    if not thread_id:
        st.title("Databricks Medallion Agent")
        st.markdown(
            "Upload a dataset and (optionally) describe the goal. The agent provisions "
            "Unity Catalog, then builds **Bronze → Silver → Gold** with human review at "
            "each step."
        )
        return

    state = state_bridge.get_state(settings, thread_id)
    interrupt = state_bridge.pending_interrupt(settings, thread_id)

    chat_col, review_col, stage_col = st.columns([1.15, 1.5, 0.9])
    with chat_col:
        render_chat(state)
    with review_col:
        render_artifact_panel(settings, thread_id, interrupt, state)
    with stage_col:
        render_stage_tracker(state)
