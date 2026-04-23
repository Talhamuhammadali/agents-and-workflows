"""Data Agent v2 — the v1 react_agent rebuilt on base_v2.

Public API:

    from agentic_patterns.data_agent_v2 import (
        DATA_AGENT_V2_BUILDER,
        DataAgentState,
        DataAgentContext,
        DATA_AGENT_V2_SYSTEM_PROMPT,
    )
"""

from agentic_patterns.data_agent_v2.agent import DATA_AGENT_V2_BUILDER
from agentic_patterns.data_agent_v2.prompts import DATA_AGENT_V2_SYSTEM_PROMPT
from agentic_patterns.data_agent_v2.state import DataAgentContext, DataAgentState

__all__ = [
    "DATA_AGENT_V2_BUILDER",
    "DATA_AGENT_V2_SYSTEM_PROMPT",
    "DataAgentContext",
    "DataAgentState",
]
