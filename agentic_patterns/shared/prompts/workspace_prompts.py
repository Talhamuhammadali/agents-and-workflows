"""Tool descriptions for workspace filesystem tools."""

READ_FILE_DESCRIPTION = (
    "Reads the contents of a file from the workspace. "
    "Use this tool when you need to view or inspect a file's content.\n"
    "Output is formatted with line numbers (cat -n style).\n"
    "If the file was already read or written in this conversation, "
    "returns an 'unchanged' signal to save context. Use force=True to always get full content.\n"
    "Parameters:\n"
    "  - path (str): Relative path to the file within the workspace (e.g. 'src/main.py').\n"
    "  - offset (int, optional): 1-indexed line to start reading from — matches the "
    "line numbers shown by Grep and read_file's cat -n output. Defaults to 1.\n"
    "  - limit (int, optional): Maximum number of lines to read. Defaults to 2000.\n"
    "  - force (bool, optional): If true, always returns full content. Defaults to false."
)

WRITE_FILE_DESCRIPTION = (
    "Creates or overwrites a file in the workspace with the given content. "
    "Use this tool when you need to create a new file or completely replace an existing file's content.\n"
    "Parameters:\n"
    "  - path (str): Relative path to the file within the workspace (e.g. 'src/main.py').\n"
    "  - content (str): The full text content to write into the file.\n"
    "Note: The parent directory must already exist. Use bash to create directories first if needed."
)

EDIT_FILE_DESCRIPTION = (
    "Performs a find-and-replace operation on a file in the workspace. "
    "Use this tool when you need to modify part of an existing file without rewriting the whole thing.\n"
    "IMPORTANT: You MUST read the file with read_file before using this tool. "
    "Never edit a file you haven't read — you need the exact content to match against.\n"
    "Parameters:\n"
    "  - path (str): Relative path to the file within the workspace (e.g. 'src/main.py').\n"
    "  - old_string (str): The exact text to find in the file. Must match exactly including "
    "whitespace and indentation. Can span multiple lines.\n"
    "  - new_string (str): The text to replace it with.\n"
    "  - replace_all (bool, optional): If true, replaces all occurrences. Defaults to false.\n"
    "Note: If old_string appears multiple times and replace_all is false, the tool will error. "
    "Provide more surrounding context to make the match unique, or set replace_all=true."
)
