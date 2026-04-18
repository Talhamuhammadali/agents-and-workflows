"""Main agent file for the React agent."""

from agentic_patterns.base import build_react_agent
from agentic_patterns.react_agent.nodes import agent_node, router
from agentic_patterns.react_agent.state import ReactAgentContextSchema, ReactAgentState
from agentic_patterns.react_agent.tools import TOOLS

REACT_AGENT_BUILDER = build_react_agent(
    agent_node=agent_node,
    router=router,
    agent_state=ReactAgentState,
    context_schema=ReactAgentContextSchema,
    tools=TOOLS,
)

graph = REACT_AGENT_BUILDER.compile()
