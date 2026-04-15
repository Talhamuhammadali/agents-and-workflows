"""Prompt constants for the subagent pattern."""

from agentic_patterns.subagent_pattern.prompts.agent_prompts import MAIN_AGENT_SYSTEM_PROMPT
from agentic_patterns.subagent_pattern.prompts.tool_prompts import (
    CREATE_FILE_DESCRIPTION,
)

__all__ = [
    "CREATE_FILE_DESCRIPTION",
    "MAIN_AGENT_SYSTEM_PROMPT",
]
