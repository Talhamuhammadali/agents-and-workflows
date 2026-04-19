"""React agent state definitions and context schema."""

from dataclasses import dataclass
from pathlib import Path
from typing import NotRequired

from langgraph.graph import MessagesState


class ReactAgentState(MessagesState):
    """State definition for Base React agent."""

    message: str
    todos: NotRequired[list[dict]]
    workspace: NotRequired[str]


@dataclass
class ReactAgentContextSchema:
    """Context schema for the React agent."""

    agent_name: str
    model: str
    workspace: Path | None = None
