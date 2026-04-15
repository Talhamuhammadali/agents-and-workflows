"""Tool descriptions for the subagent pattern tools."""

CREATE_FILE_DESCRIPTION = (
    "Creates a file with the given name and content in an in-memory file system. "
    "Use this tool when the user asks to create, write, or save a new file. "
    "Parameters:\n"
    "  - file_name (str): The name of the file to create (e.g. 'notes.txt').\n"
    "  - content (str): The full text content to write into the file.\n"
    "The file is stored per-agent and per-thread so each conversation has its own filesystem."
)

UPDATE_TODOS_DESCRIPTION = (
    "Overwrites the entire todos list in state with the provided list. "
    "Use this tool whenever a todo is added, removed, or its completion status changes. "
    "You must regenerate the FULL list every time — this is a replace, not a patch.\n"
    "Parameters:\n"
    "  - todos (list[dict]): The complete list of todo items. "
    "Each item must have the keys:\n"
    "      - id (int): Unique identifier for the todo.\n"
    "      - task (str): Description of what needs to be done.\n"
    "      - completed (bool): Whether the todo is finished.\n"
    "Example:\n"
    '  [{"id": 1, "task": "Buy groceries", "completed": false}, '
    '{"id": 2, "task": "Walk the dog", "completed": true}]'
)
