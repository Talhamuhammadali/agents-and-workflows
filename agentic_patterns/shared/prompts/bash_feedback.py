"""Feedback messages for bash tools."""

BASH_SUCCESS = "{output}"
BASH_TRUNCATED = "{prefix} Output truncated (exceeded ~{max_tokens} tokens, showing tail):\n{output}"
BASH_ERROR_EMPTY = "{prefix} Error: Empty command."
BASH_ERROR_BLOCKED = "{prefix} Error: Command blocked — {reason}"

SEARCH_NO_MATCHES = "{prefix} No matches for pattern '{pattern}' under '{path}'."
SEARCH_ERROR_NOT_FOUND = "{prefix} Error: Directory not found: {path}"
SEARCH_ERROR_PERMISSION = "{prefix} Error: Permission denied — path '{path}' escapes the workspace."
GREP_ERROR_INVALID_REGEX = "{prefix} Error: Invalid regex '{pattern}' — {reason}"

BASH_FEEDBACK = {
    "bash_success": BASH_SUCCESS,
    "bash_truncated": BASH_TRUNCATED,
    "bash_error_empty": BASH_ERROR_EMPTY,
    "bash_error_blocked": BASH_ERROR_BLOCKED,
    "search_no_matches": SEARCH_NO_MATCHES,
    "search_error_not_found": SEARCH_ERROR_NOT_FOUND,
    "search_error_permission": SEARCH_ERROR_PERMISSION,
    "grep_error_invalid_regex": GREP_ERROR_INVALID_REGEX,
}
