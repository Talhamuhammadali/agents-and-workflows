"""System prompt for the Data Agent v2.

Leaner than the v1 prompt: tool-combo advice has moved into the fileops
SKILL.md body, loaded on-demand via the Skill tool. This prompt only carries
role + always-relevant behaviour.
"""

DATA_AGENT_V2_SYSTEM_PROMPT = """You are a helpful assistant for performing data-related tasks."""
