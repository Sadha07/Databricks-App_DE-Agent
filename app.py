"""Databricks Apps / local Streamlit entrypoint.

This file is intentionally thin: it delegates all rendering to the UI layer so
that the agent and services never depend on Streamlit. Databricks Apps runs this
via the command declared in ``app.yaml``.
"""

from __future__ import annotations


from de_agent.config.logging import configure_logging
from de_agent.config.settings import get_settings
from de_agent.ui.main import render


def _bootstrap() -> None:
    settings = get_settings()
    configure_logging(settings)
    render(settings)


if __name__ == "__main__":
    _bootstrap()
else:
    # Streamlit imports the module rather than running __main__.
    _bootstrap()
