"""Tools available to the React agent."""

from agentic_patterns.shared import FILE_TOOLS, bash, update_todos

TOOLS: list = [update_todos, bash, *FILE_TOOLS]
