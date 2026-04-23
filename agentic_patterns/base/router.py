"""Default router — routes the last AI message to ``tools`` or ``end``.

Agents that need bespoke routing (e.g. subagent delegation) can pass their
own callable into ``build_agent``.
"""

from langchain_core.messages import AIMessage

from agentic_patterns.base.schemas import State


def default_router(state: State) -> str:
    """Route to ``tools`` when the last AI message called a tool, else ``end``."""
    # ``messages`` is required on BaseAgentState / MessagesState — index rather
    # than .get() so mypy sees list[BaseMessage] and not object.
    messages = state["messages"]
    if not messages:
        return "end"
    last_message = messages[-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"
    return "end"
