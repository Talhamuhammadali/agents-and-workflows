"""Tools available to the React agent."""

from agentic_patterns.shared import BASH_TOOLS, FILE_TOOLS, update_todos

TOOLS: list = [update_todos, *BASH_TOOLS, *FILE_TOOLS]
