"""Chat panel — renders the agent/human conversation from graph state."""

from __future__ import annotations

from typing import Any

import streamlit as st


def render_chat(state: dict[str, Any]) -> None:
    st.subheader("Conversation")
    messages = state.get("messages", [])
    if not messages:
        st.info("Upload a dataset and start a build to begin.")
        return
    for msg in messages:
        role = _role_of(msg)
        with st.chat_message(role):
            st.markdown(_content_of(msg))


def _role_of(msg: Any) -> str:
    msg_type = getattr(msg, "type", None)
    if msg_type == "human":
        return "user"
    return "assistant"


def _content_of(msg: Any) -> str:
    content = getattr(msg, "content", msg)
    return content if isinstance(content, str) else str(content)
