"""Feedback messages for the Skill tool."""

# Success: the skill's own instructions are the payload (no [SYSTEM] wrapper).
# Same shape as READ_SUCCESS / ASK_QUESTION — the body is the main deliverable.
SKILL_LOADED = "{instructions}"

SKILL_ERROR_UNKNOWN = "{prefix} Error: Unknown skill {name!r}. Registered skills: {registered}."
SKILL_ERROR_NOT_PERMITTED = "{prefix} Error: Skill {name!r} is not available to this agent. Allowed skills: {allowed}."

SKILL_FEEDBACK = {
    "skill_loaded": SKILL_LOADED,
    "skill_error_unknown": SKILL_ERROR_UNKNOWN,
    "skill_error_not_permitted": SKILL_ERROR_NOT_PERMITTED,
}
