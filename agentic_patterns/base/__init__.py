"""base_v2 — generic agent framework (node + builder + schemas).

The skill subsystem (Skill tool + registry + library) lives in
``agentic_patterns.shared``. Import from there for skill primitives.

Public API:

    from agentic_patterns.base_v2 import (
        BaseAgentState, BaseAgentContext, State, Context,
        agent_node, default_router, build_agent,
    )
"""

from agentic_patterns.base.builder import build_agent
from agentic_patterns.base.node import agent_node
from agentic_patterns.base.router import default_router
from agentic_patterns.base.schemas import (
    BaseAgentContext,
    BaseAgentState,
    Context,
    State,
)

__all__ = [
    "BaseAgentState",
    "BaseAgentContext",
    "State",
    "Context",
    "agent_node",
    "default_router",
    "build_agent",
]
