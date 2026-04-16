"""Feedback messages for workspace filesystem tools."""

SYSTEM_PREFIX = "[SYSTEM]"

WRITE_SUCCESS = "{prefix} File written successfully: {path}"
WRITE_ERROR_NO_PARENT = "{prefix} Error: Parent directory does not exist for '{path}'. Create it first."
WRITE_ERROR_PERMISSION = "{prefix} Error: Permission denied — path '{path}' escapes the workspace."

EDIT_SUCCESS = "{prefix} File edited successfully: {path}\n{diff}"
EDIT_ERROR_NOT_FOUND = "{prefix} Error: File not found: {path}"
EDIT_ERROR_STRING_NOT_FOUND = (
    "{prefix} Error: old_string not found in '{path}'. "
    "The file may have changed. Use read_file to get the current content before editing."
)
EDIT_ERROR_MULTIPLE = (
    "{prefix} Error: Multiple occurrences of old_string found in '{path}'. "
    "Provide more surrounding context to make the match unique, or set replace_all=true."
)
EDIT_ERROR_PERMISSION = "{prefix} Error: Permission denied — path '{path}' escapes the workspace."

READ_SUCCESS = "{content}"
READ_UNCHANGED = "{prefix} File unchanged since last read: {path}. Use that as it is still valid."
READ_ERROR_NOT_FOUND = "{prefix} Error: File not found: {path}"
READ_ERROR_PERMISSION = "{prefix} Error: Permission denied — path '{path}' escapes the workspace."


FEEDBACK = {
    "read_success": READ_SUCCESS,
    "write_success": WRITE_SUCCESS,
    "write_error_no_parent": WRITE_ERROR_NO_PARENT,
    "write_error_permission": WRITE_ERROR_PERMISSION,
    "edit_success": EDIT_SUCCESS,
    "edit_error_not_found": EDIT_ERROR_NOT_FOUND,
    "edit_error_string_not_found": EDIT_ERROR_STRING_NOT_FOUND,
    "edit_error_multiple": EDIT_ERROR_MULTIPLE,
    "edit_error_permission": EDIT_ERROR_PERMISSION,
    "read_unchanged": READ_UNCHANGED,
    "read_error_not_found": READ_ERROR_NOT_FOUND,
    "read_error_permission": READ_ERROR_PERMISSION,
}


def feedback(key: str, **kwargs: dict) -> str:
    """Return a formatted feedback message for a given key and kwargs."""
    return FEEDBACK[key].format(prefix=SYSTEM_PREFIX, **kwargs)
