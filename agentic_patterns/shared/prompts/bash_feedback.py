"""Feedback messages for bash tools."""

BASH_SUCCESS = "{output}"
BASH_TRUNCATED = "{prefix} Output truncated (exceeded ~{max_tokens} tokens, showing tail):\n{output}"
BASH_ERROR_EMPTY = "{prefix} Error: Empty command."
BASH_ERROR_BLOCKED = "{prefix} Error: Command blocked — {reason}"

BASH_FEEDBACK = {
    "bash_success": BASH_SUCCESS,
    "bash_truncated": BASH_TRUNCATED,
    "bash_error_empty": BASH_ERROR_EMPTY,
    "bash_error_blocked": BASH_ERROR_BLOCKED,
}
