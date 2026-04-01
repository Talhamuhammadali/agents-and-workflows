"""Node functions for the subagent pattern graph."""
from langchain.chat_models import BaseChatModel
from langgraph.prebuilt import ToolNode

from agentic_pattern.subagent_pattern.state import AgentState


# TODO 1: Define tools (create_file, todos)
# - create_file: creates a file with given name and content
# - todos: manages a todo list (add/list/complete)

# TODO 2: Create the tool node
# tool_node = ToolNode(tools=[...])

# TODO 3: Define the LLM node
# def llm_node(state: State) -> dict:
#     """Call the LLM with tools and subagents bound."""
#     # Bind tools to LLM
#     # Invoke LLM with state messages
#     # Return updated messages
#     pass

# TODO 4: Define the subagent node
# def subagent_node(state: State) -> dict:
#     """Delegate work to a subagent (a separate compiled graph)."""
#     # Invoke the subagent graph with relevant context
#     # Return the subagent's response as messages
#     pass

# TODO 5: Define the router function
# def route_llm_output(state: State) -> str:
#     """Route based on the last LLM message.
#
#     Returns:
#         "tools" - if LLM called a tool
#         "subagents" - if LLM wants to delegate to a subagent
#         "__end__" - if LLM is done (final text response)
#     """
#     pass
