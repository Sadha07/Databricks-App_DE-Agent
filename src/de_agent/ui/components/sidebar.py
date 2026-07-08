"""Sidebar — dataset upload, business instruction, and run controls."""

from __future__ import annotations

from typing import TYPE_CHECKING

import streamlit as st

from de_agent.ui import state_bridge

if TYPE_CHECKING:
    from de_agent.config.settings import Settings


def render_sidebar(settings: Settings) -> None:
    with st.sidebar:
        st.header("Medallion builder")
        st.caption(f"catalog: `{settings.target_catalog}` · env: `{settings.environment.value}`")

        uploaded = st.file_uploader("Dataset (CSV)", type=["csv"])
        instruction = st.text_area(
            "Business instruction (optional)",
            placeholder="e.g. Build a sales star schema with revenue by month and customer.",
        )

        disabled = uploaded is None or st.session_state.get("thread_id") is not None
        if st.button("Start build", type="primary", disabled=disabled) and uploaded is not None:
            thread_id = state_bridge.start_run(
                settings,
                business_instruction=instruction or "",
                filename=uploaded.name,
                data=uploaded.getvalue(),
            )
            st.session_state["thread_id"] = thread_id
            st.rerun()

        if st.session_state.get("thread_id"):
            st.divider()
            if st.button("New run"):
                st.session_state.pop("thread_id", None)
                st.rerun()
