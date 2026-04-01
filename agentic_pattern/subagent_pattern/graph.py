"""Graph definition for the subagent pattern."""
from langgraph.graph import StateGraph, START, END

from agentic_pattern.subagent_pattern.state import State


# TODO 1: Import nodes and router from nodes.py
# from agentic_pattern.subagent_pattern.nodes import (
#     llm_node,
#     tool_node,
#     subagent_node,
#     route_llm_output,
# )

# TODO 2: Build the graph
# graph_builder = StateGraph(State)

# TODO 3: Add nodes
# graph_builder.add_node("llm", llm_node)
# graph_builder.add_node("tools", tool_node)
# graph_builder.add_node("subagents", subagent_node)

# TODO 4: Add edges
# graph_builder.add_edge(START, "llm")
# graph_builder.add_conditional_edges("llm", route_llm_output)
# graph_builder.add_edge("tools", "llm")       # tools -> back to LLM
# graph_builder.add_edge("subagents", "llm")    # subagents -> back to LLM

# TODO 5: Compile
# graph = graph_builder.compile()
