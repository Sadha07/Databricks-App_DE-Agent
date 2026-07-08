"""Dataset profiling node."""

from __future__ import annotations

from langchain_core.runnables import RunnableConfig

import base64
from typing import Any

from de_agent.agent.nodes._helpers import ai, record_error
from de_agent.agent.state import Layer, StageStatus
from de_agent.config.logging import get_logger
from de_agent.services.container import get_container

log = get_logger(__name__)


def profiling_node(state: dict[str, Any], config: RunnableConfig) -> dict[str, Any]:
    container = get_container(config)
    try:
        data = base64.b64decode(state["raw_bytes_b64"])
        profile = container.profiler.profile_csv_bytes(data)
    except Exception as exc:  # noqa: BLE001
        return {
            "errors": record_error(state, node="profiling", message=str(exc)),
            "layer_status": {**state["layer_status"], Layer.BRONZE.value: StageStatus.FAILED.value},
            "messages": [ai(f"Profiling failed: {exc}")],
        }
    log.info("profiling.done", rows=profile.row_count, cols=profile.column_count)
    return {
        "profile": profile.model_dump(),
        "messages": [ai(f"Profiled dataset: {profile.row_count} rows, {profile.column_count} cols.")],
    }
