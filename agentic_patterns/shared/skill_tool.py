"""The Skill tool: load a skill into the live agent.

Exposed to the LLM as ``Skill``. The Python function is ``read_skill`` to
avoid shadowing the Skill dataclass.

Feedback shapes match the rest of the toolbelt — success and errors both go
through ``feedback()`` / ``tool_reply()`` from shared.helper.
"""

from langchain_core.tools import tool
from langgraph.prebuilt import ToolRuntime
from langgraph.types import Command

from agentic_patterns.shared.helper import tool_reply
from agentic_patterns.shared.prompts.skill_prompts import SKILL_TOOL_DESCRIPTION
from agentic_patterns.shared.skill_registry import (
    ESSENTIAL_TOOL_NAMES,
    SKILLS,
    TOOLS_BY_NAME,
)


@tool(name_or_callable="Skill", description=SKILL_TOOL_DESCRIPTION)
def read_skill(name: str, tool_runtime: ToolRuntime) -> Command:
    """Load a skill: deliver its instructions and expand active_tools.

    Essentials remain in active_tools regardless of state history; repeat
    loads are idempotent via set-union.
    """
    # Allow-list gate — each agent's context declares which skills it may load.
    available = list(getattr(tool_runtime.context, "available_skills", None) or [])
    if name not in available:
        return tool_reply(
            tool_runtime,
            "skill_error_not_permitted",
            name=name,
            allowed=sorted(available),
        )

    if name not in SKILLS:
        return tool_reply(
            tool_runtime,
            "skill_error_unknown",
            name=name,
            registered=sorted(SKILLS),
        )

    skill = SKILLS[name]
    current = list(getattr(tool_runtime, "state", {}).get("active_tools") or [])

    # Invariant: essentials ALWAYS present, regardless of state history.
    merged = list({*ESSENTIAL_TOOL_NAMES, *current, *skill.allowed_tools})

    # Build the success message via the feedback pipeline, then extend the
    # Command with the active_tools update (tool_reply only writes messages).
    return tool_reply(
        tool_runtime, "skill_loaded", instructions=skill.instructions, state_update={"active_tools": merged}
    )


# Self-register into the shared tool registry so ``resolve()`` can look it up.
# Done here (not in skill_registry.py) to avoid a circular import.
TOOLS_BY_NAME[read_skill.name] = read_skill
