"""Graph builder — one entry point for every agent built on base_v2.

Callers no longer write an agent_node. They pass:
  - tools:          the full tool set the graph's ToolNode can execute
                    (must include every tool any skill may unlock)
  - state_schema:   their agent's state (must extend BaseAgentState)
  - context_schema: their agent's context (must extend BaseAgentContext)
  - router:         optional override for bespoke routing needs

The system prompt is NOT a builder argument. It lives on
``context.system_prompt`` — the generic ``agent_node`` reads it at invoke time.
"""

from collections.abc import Callable

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from agentic_patterns.base.node import agent_node
from agentic_patterns.base.router import default_router
from agentic_patterns.base.schemas import Context, State


def build_agent(
    tools: list,
    state_schema: type[State],
    context_schema: type[Context],
    router: Callable[[State], str] | None = None,
) -> StateGraph[State, Context, State, State]:
    """Assemble the ReAct graph. Returns the uncompiled builder."""
    router = router or default_router

    graph: StateGraph[State, Context, State, State] = StateGraph(state_schema, context_schema=context_schema)

    graph.add_node("agent", agent_node)  # type: ignore[call-overload]
    graph.add_node("tools", ToolNode(tools))

    graph.add_edge(START, "agent")
    graph.add_conditional_edges(
        "agent",
        router,
        {"tools": "tools", "end": END},
    )
    graph.add_edge("tools", "agent")

    return graph
