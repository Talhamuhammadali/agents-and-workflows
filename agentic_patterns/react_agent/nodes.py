"""Fixed graph nodes for react agent."""

from langchain.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime

from agentic_patterns.react_agent.state import ReactAgentState


async def agent_node(state: ReactAgentState, config: RunnableConfig, runtime: Runtime) -> dict:
    """Create context and messages and generates responses."""
    return {}


async def router(state: ReactAgentState) -> str:
    """Route the LLM output to the appropriate next node."""
    last_message = state.get("messages", [])[-1]

    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"
    else:
        return "end"
