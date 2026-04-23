
from dataclasses import dataclass, field
from typing import TypeVar

from langgraph.graph import MessagesState

@dataclass
class ContextSchema:
    """State definition for Base React agent."""

    message: str
    todos: list[dict] = field(default_factory=list)
    workspace: str = ""

class ExtendedReactAgentState(MessagesState):
    """Extended state definition for React agent with additional fields."""

    message: str
    todos: list[dict]
    workspace: str = ""
    
S = TypeVar("S", bound=MessagesState)
C = TypeVar("C", bound=ContextSchema)