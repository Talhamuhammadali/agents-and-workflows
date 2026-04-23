"""Build the Data Agent v2 graph.

No hand-written node, no hand-written router — the generic ``build_agent``
from ``base_v2`` handles both. Callers compile this builder with their own
checkpointer/store, and invoke it with a ``DataAgentContext`` that carries
``system_prompt`` + ``available_skills``.
"""

from agentic_patterns.base import build_agent
from agentic_patterns.data_agent_v2.state import DataAgentContext, DataAgentState
from agentic_patterns.shared.skill_registry import TOOLS_BY_NAME

_ALL_TOOLS = list(TOOLS_BY_NAME.values())

DATA_AGENT_V2_BUILDER = build_agent(
    tools=_ALL_TOOLS,
    state_schema=DataAgentState,
    context_schema=DataAgentContext,
)
