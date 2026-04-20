"""Prompts related to todo list management."""

UPDATE_TODOS_DESCRIPTION = (
    "Overwrites the entire todos list in state with the provided list. "
    "Use this tool to track multi-step work: add items when planning, flip an "
    "item to 'in_progress' RIGHT BEFORE you start that step, and mark it "
    "'completed' AS SOON AS the step is done.\n\n"
    "Status lifecycle:\n"
    "  - pending: planned but not started.\n"
    "  - in_progress: you are actively working on it right now. Keep at most "
    "ONE item in this state at a time — it signals the current focus to the user.\n"
    "  - completed: done.\n\n"
    "Call this tool whenever a status changes — do not batch status updates "
    "across multiple steps. You must regenerate the FULL list every time — "
    "this is a replace, not a patch.\n\n"
    "Parameters:\n"
    "  - todos (list[dict]): The complete list of todo items. Each item:\n"
    "      - id (int): Unique identifier for the todo.\n"
    "      - task (str): Description of what needs to be done.\n"
    "      - status (str): One of 'pending' | 'in_progress' | 'completed'.\n\n"
    "Example:\n"
    '  [{"id": 1, "task": "Read config", "status": "completed"}, '
    '{"id": 2, "task": "Parse entries", "status": "in_progress"}, '
    '{"id": 3, "task": "Write report", "status": "pending"}]'
    "\n\n**Important:** call this tool on its own — don't batch with other tool calls, "
    "so the UI reflects the current state in real time."
)
