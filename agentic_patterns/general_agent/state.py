"""State + context for the Data Agent v2.

Extends the base contracts from ``base_v2`` with the two fields the current
data agent actually uses: a ``workspace`` path (for filesystem scoping) and a
``todos`` list (produced by the Todos tool).
"""

from dataclasses import dataclass
from pathlib import Path
from typing import NotRequired

from agentic_patterns.base.schemas import BaseAgentContext, BaseAgentState


class DataAgentState(BaseAgentState):
    """Inherits ``message`` + ``messages`` + ``active_tools`` from base."""

    todos: NotRequired[list[dict]]
    workspace: NotRequired[str]


@dataclass
class DataAgentContext(BaseAgentContext):
    """Inherits ``agent_name``, ``model``, ``system_prompt``, ``available_skills``,
    and the compaction hook fields from base. Adds the workspace path that the
    filesystem tools read at runtime.
    """

    workspace: Path | None = None
