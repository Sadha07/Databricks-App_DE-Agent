"""Stage tracker — Bronze/Silver/Gold progress with per-layer status."""

from __future__ import annotations

from typing import Any

import streamlit as st

from de_agent.agent.state import Layer
from de_agent.ui.theme import status_icon


def render_stage_tracker(state: dict[str, Any]) -> None:
    st.subheader("Pipeline")
    status = state.get("layer_status", {})
    tables = state.get("tables_by_layer", {})

    steps = [
        ("Setup + profile", "done" if state.get("landing_table") else "pending"),
        ("Bronze", status.get(Layer.BRONZE.value, "pending")),
        ("Silver", status.get(Layer.SILVER.value, "pending")),
        ("Gold", status.get(Layer.GOLD.value, "pending")),
    ]
    for label, st_value in steps:
        st.markdown(f"{status_icon(st_value)} **{label}** — `{st_value}`")
        layer_key = label.lower()
        if layer_key in tables:
            st.caption(tables[layer_key])

    errors = state.get("errors", [])
    if errors:
        with st.expander(f"Errors ({len(errors)})"):
            for err in errors:
                st.error(f"{err.get('node')}: {err.get('message')}")
