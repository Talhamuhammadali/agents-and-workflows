"""Node functions for the subagent pattern graph."""

from langgraph.prebuilt import ToolNode
from langgraph.runtime import Runtime

from agentic_pattern.subagent_pattern.state import AgentState

# TODO 2: Create the tool node
tool_node = ToolNode(tools=[])


# TODO 3: Define the LLM node
def llm_node(state: AgentState, runtime: Runtime) -> dict:  # type: ignore[type-arg]
    """Call the LLM with tools and subagents bound."""
    # Bind tools to LLM
    # Invoke LLM with state messages
    # Return updated messages
    raise NotImplementedError


# TODO 4: Define the subagent node
def subagent_node(state: AgentState, runtime: Runtime) -> dict:  # type: ignore[type-arg]
    """Delegate work to a subagent (a separate compiled graph)."""
    # Invoke the subagent graph with relevant context
    # Return the subagent's response as messages
    raise NotImplementedError


# TODO 5: Define the router function
def route_llm_output(state: AgentState, runtime: Runtime) -> str:
    """Route based on the last LLM message.

    Returns:
        "tools" - if LLM called a tool
        "subagents" - if LLM wants to delegate to a subagent
        "__end__" - if LLM is done (final text response)
    """
    raise NotImplementedError
