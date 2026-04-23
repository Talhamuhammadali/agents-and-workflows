"""Base state and context schemas shared by every agent built on base_v2.

The rule: a base field exists here ONLY if the generic ``agent_node`` reads it.
Everything else (workspace, todos, auto_accept, ...) belongs on a subclass
of the concrete agent.
"""

from dataclasses import dataclass
from typing import NotRequired, TypeVar

from langgraph.graph import MessagesState


class BaseAgentState(MessagesState):
    """Minimum state. Concrete agents extend with their own NotRequired fields."""

    message: str | dict
    workspace: NotRequired[str]
    active_tools: NotRequired[list[str]]


@dataclass
class BaseAgentContext:
    """Minimum context. Prebuilt outside the graph, immutable per run."""

    agent_name: str
    model: str
    system_prompt: str  # assembled outside the graph
    available_skills: list[str] | None = None  # allow-list gate for read_skill
    compaction: str | None = None  # hook; impl deferred
    compaction_prompt: str | None = None


State = TypeVar("State", bound=BaseAgentState)
Context = TypeVar("Context", bound=BaseAgentContext)
