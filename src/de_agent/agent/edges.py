"""Conditional routing between nodes.

Linear medallion flow with a failure short-circuit: any layer that ends in FAILED
routes straight to the terminal node so the run stops cleanly (the retry loops that
could recover already ran inside the build node).
"""

from __future__ import annotations

from typing import Any, Literal

from langgraph.graph import END

from de_agent.agent.state import Layer, StageStatus


def _failed(state: dict[str, Any], layer: str) -> bool:
    return state.get("layer_status", {}).get(layer) == StageStatus.FAILED.value


def route_after_setup(state: dict[str, Any]) -> Literal["profiling", "__end__"]:
    return END if _failed(state, Layer.BRONZE.value) else "profiling"


def route_after_bronze(state: dict[str, Any]) -> Literal["silver", "__end__"]:
    return END if _failed(state, Layer.BRONZE.value) else "silver"


def route_after_silver(state: dict[str, Any]) -> Literal["gold_reasoning", "__end__"]:
    return END if _failed(state, Layer.SILVER.value) else "gold_reasoning"


def route_after_gold_build(state: dict[str, Any]) -> Literal["finalize", "__end__"]:
    return END if _failed(state, Layer.GOLD.value) else "finalize"
