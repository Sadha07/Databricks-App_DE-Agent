#!/usr/bin/env bash
# Run the app locally with in-memory fakes (no cloud, no API keys required).
set -euo pipefail
export DE_AGENT_ENV=local
export LLM_PROVIDER="${LLM_PROVIDER:-fake}"
export REQUIRE_APPROVAL="${REQUIRE_APPROVAL:-true}"
uv run streamlit run app.py
