"""Tools available to the React agent."""

from agentic_patterns.shared import BASH_TOOLS, FILE_TOOLS, ask_question, update_todos

TOOLS: list = [update_todos, ask_question, *BASH_TOOLS, *FILE_TOOLS]
