"""Prompt for the Skill tool — the loader that expands an agent's capabilities."""

SKILL_TOOL_DESCRIPTION = (
    "Load a skill to expand your capabilities. A skill bundles (1) detailed "
    "instructions on when and how to handle a class of tasks and (2) the "
    "specific tools needed to carry out that work.\n"
    "Parameters:\n"
    "  - name (str): The skill name to load. Must appear in this agent's "
    "available_skills list.\n"
)
