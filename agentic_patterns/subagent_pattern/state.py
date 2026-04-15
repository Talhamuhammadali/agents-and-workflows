"""State definition for the subagent pattern graph."""

from dataclasses import dataclass

from langgraph.graph import MessagesState

from utils import Model


class AgentState(MessagesState):
    """Graph state for the subagent pattern.

    Attributes:
        messages: Conversation message history (auto-appended via add_messages reducer).
    """

    message: str
    todos: list[dict]


@dataclass
class ContextSchema:
    """Context schema for the subagent pattern graph.

    This defines the context variables that can be used for tool calls and subagent delegation.
    """

    agent_name: str
    model: Model
    subagents: list[str]
