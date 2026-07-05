"""Build the infrastructure agent graph."""

from agentic_patterns.base import build_agent
from agentic_patterns.infra_agent.state import InfraAgentContext, InfraAgentState
from agentic_patterns.infra_agent.tools import INFRA_TOOLS
from agentic_patterns.shared.skill_registry import TOOLS_BY_NAME

TOOLS = list({tool.name: tool for tool in [*TOOLS_BY_NAME.values(), *INFRA_TOOLS]}.values())

INFRA_AGENT_BUILDER = build_agent(
    tools=TOOLS,
    state_schema=InfraAgentState,
    context_schema=InfraAgentContext,
)
