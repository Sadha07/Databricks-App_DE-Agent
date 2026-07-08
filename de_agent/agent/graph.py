"""Graph assembly.

Wires the medallion flow:

    clarification → environment_setup → profiling → planning
      → bronze → silver → gold_reasoning → gold_planning → gold_build → finalize

Human-in-the-loop pauses are dynamic (``interrupt()`` inside clarification, the
build loop's approval gate, and gold confirmation), so no static ``interrupt_before``
is needed. State is durable via the injected checkpointer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from langgraph.graph import END, START, StateGraph

from de_agent.agent.edges import (
    route_after_bronze,
    route_after_gold_build,
    route_after_setup,
    route_after_silver,
)
from de_agent.agent.nodes.bronze import bronze_node
from de_agent.agent.nodes.clarification import clarification_node
from de_agent.agent.nodes.environment_setup import environment_setup_node
from de_agent.agent.nodes.finalize import finalize_node
from de_agent.agent.nodes.gold_build import gold_build_node
from de_agent.agent.nodes.gold_planning import gold_planning_node
from de_agent.agent.nodes.gold_reasoning import gold_reasoning_node
from de_agent.agent.nodes.planning import planning_node
from de_agent.agent.nodes.profiling import profiling_node
from de_agent.agent.nodes.silver import silver_node
from de_agent.agent.state import AgentState

if TYPE_CHECKING:
    from langgraph.checkpoint.base import BaseCheckpointSaver
    from langgraph.graph.state import CompiledStateGraph


def build_graph(checkpointer: BaseCheckpointSaver) -> CompiledStateGraph:
    g: StateGraph = StateGraph(AgentState)

    g.add_node("clarification", clarification_node)
    g.add_node("environment_setup", environment_setup_node)
    g.add_node("profiling", profiling_node)
    g.add_node("planning", planning_node)
    g.add_node("bronze", bronze_node)
    g.add_node("silver", silver_node)
    g.add_node("gold_reasoning", gold_reasoning_node)
    g.add_node("gold_planning", gold_planning_node)
    g.add_node("gold_build", gold_build_node)
    g.add_node("finalize", finalize_node)

    g.add_edge(START, "clarification")
    g.add_edge("clarification", "environment_setup")
    g.add_conditional_edges("environment_setup", route_after_setup)
    g.add_edge("profiling", "planning")
    g.add_edge("planning", "bronze")
    g.add_conditional_edges("bronze", route_after_bronze)
    g.add_conditional_edges("silver", route_after_silver)
    g.add_edge("gold_reasoning", "gold_planning")
    g.add_edge("gold_planning", "gold_build")
    g.add_conditional_edges("gold_build", route_after_gold_build)
    g.add_edge("finalize", END)

    return g.compile(checkpointer=checkpointer)
