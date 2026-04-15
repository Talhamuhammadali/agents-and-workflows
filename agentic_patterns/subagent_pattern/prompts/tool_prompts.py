"""Tool descriptions for the subagent pattern tools."""

CREATE_FILE_DESCRIPTION = (
    "Creates a file with the given name and content in an in-memory file system. "
    "Use this tool when the user asks to create, write, or save a new file. "
    "Parameters:\n"
    "  - file_name (str): The name of the file to create (e.g. 'notes.txt').\n"
    "  - content (str): The full text content to write into the file.\n"
    "The file is stored per-agent and per-thread so each conversation has its own filesystem."
)
