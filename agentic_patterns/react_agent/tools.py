"""Tools available to the React agent."""

from agentic_patterns.shared import FILE_TOOLS, update_todos

TOOLS: list = [update_todos, *FILE_TOOLS]
