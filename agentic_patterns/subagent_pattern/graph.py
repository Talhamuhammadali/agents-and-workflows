"""Graph definition for the subagent pattern."""

# TODO 1: Import nodes and router from nodes.py
from agentic_pattern.subagent_pattern.nodes import (
    agent_node,
    route_llm_output,
    subagent_node,
    tool_node,
)
from agentic_pattern.subagent_pattern.state import AgentState, ContextSchema
from langgraph.graph import END, START, StateGraph

# Build the harness
Agent_Builder = StateGraph(AgentState, context_schema=ContextSchema)

# Add nodes
Agent_Builder.add_node("agent", agent_node)
Agent_Builder.add_node("tools", tool_node)
Agent_Builder.add_node("subagents", subagent_node)

# Add edges
Agent_Builder.add_edge(START, "agent")
Agent_Builder.add_conditional_edges(
    "agent",
    route_llm_output,
    {
        "tools": "tools",
        "subagents": "subagents",
        "turn_end": END,
    },
)
Agent_Builder.add_edge("tools", "agent")  # tools -> back to agent
Agent_Builder.add_edge("subagents", "agent")  # subagents -> back to agent

# Compile
graph = Agent_Builder.compile()
