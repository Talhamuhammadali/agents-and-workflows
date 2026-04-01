"""Graph definition for the subagent pattern."""

from langgraph.graph import START, StateGraph

# TODO 1: Import nodes and router from nodes.py
from agentic_pattern.subagent_pattern.nodes import (
    agent_node,
    route_llm_output,
    subagent_node,
    tool_node,
)
from agentic_pattern.subagent_pattern.state import AgentState

# Build the graph
graph_builder = StateGraph(AgentState)

# Add nodes
graph_builder.add_node("agent", agent_node)
graph_builder.add_node("tools", tool_node)
graph_builder.add_node("subagents", subagent_node)

# Add edges
graph_builder.add_edge(START, "agent")
graph_builder.add_conditional_edges(
    "agent",
    route_llm_output,
    {
        "tools": "tools",
        "subagents": "subagents",
    },
)
graph_builder.add_edge("tools", "agent")  # tools -> back to agent
graph_builder.add_edge("subagents", "agent")  # subagents -> back to agent

# Compile
graph = graph_builder.compile()
