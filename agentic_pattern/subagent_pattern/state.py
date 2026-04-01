"""State definition for the subagent pattern graph."""
from langgraph.graph import MessagesState

class AgentState(MessagesState):
    """Graph state for the subagent pattern.

    Attributes:
        messages: Conversation message history (auto-appended via add_messages reducer).
    """
    message: str
    todos: list[dict]