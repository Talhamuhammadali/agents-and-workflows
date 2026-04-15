"""Graph definition for a react agent."""

from collections.abc import Callable

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.typing import ContextT, StateT


# I know langchain has create_agent, this is just to learn
def build_react_agent(
    agent_node: Callable, router: Callable, agent_state: StateT, context_schema: ContextT, tools: list
) -> StateGraph:
    """Build the graph for the React agent with configurations."""
    # Build the harness
    Agent_Builder = StateGraph(agent_state, context_schema=context_schema)

    # Add nodes
    Agent_Builder.add_node("agent", agent_node)
    Agent_Builder.add_node("tools", ToolNode(tools))

    # Add edges
    Agent_Builder.add_edge(START, "agent")
    Agent_Builder.add_conditional_edges(
        "agent",
        router,
        {
            "tools": "tools",
            "end": END,
        },
    )
    Agent_Builder.add_edge("tools", "agent")

    return Agent_Builder
