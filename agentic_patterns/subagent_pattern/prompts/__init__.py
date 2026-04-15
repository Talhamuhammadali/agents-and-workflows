"""Prompt constants for the subagent pattern."""

from agentic_pattern.subagent_pattern.prompts.agent_prompts import MAIN_AGENT_SYSTEM_PROMPT
from agentic_pattern.subagent_pattern.prompts.tool_prompts import (
    CREATE_FILE_DESCRIPTION,
    UPDATE_TODOS_DESCRIPTION,
)

__all__ = [
    "CREATE_FILE_DESCRIPTION",
    "UPDATE_TODOS_DESCRIPTION",
    "MAIN_AGENT_SYSTEM_PROMPT",
]
