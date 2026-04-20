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
    "Sizing & phasing:\n"
    "  - Keep each todo to a short one-line task — not a paragraph or a summary.\n"
    "  - Keep the active list to 5-6 items. Long lists (16+) are a smell — you're "
    "planning at the wrong granularity.\n"
    "  - For complex work, break it into phases. Each phase is its own short "
    "list, and the last todo of a phase should point at the next phase so the "
    "handoff is explicit.\n"
    "  - When a phase completes, collapse its finished items into a single "
    "one-line 'completed' marker (a short phase label, not a summary) so the "
    "history stays visible, then expand the next phase's todos below it.\n\n"
    "Parameters:\n"
    "  - todos (list[dict]): The complete list of todo items. Each item:\n"
    "      - id (int): Unique identifier for the todo.\n"
    "      - task (str): Description of what needs to be done.\n"
    "      - status (str): One of 'pending' | 'in_progress' | 'completed'.\n\n"
    "Example:\n"
    '  [{"id": 1, "task": "Read config", "status": "completed"}, '
    '{"id": 2, "task": "Parse entries", "status": "in_progress"}, '
    '{"id": 3, "task": "Write report", "status": "pending"}]'
    "\n\n"
    "Scenario — phased work:\n"
    "  User asks: 'Refactor the ingestion pipeline, add tests, and wire it into "
    "CI.' That's three phases. Start with phase 1 only:\n"
    '    [{"id": 1, "task": "Map current ingestion call sites", "status": "in_progress"},\n'
    '     {"id": 2, "task": "Extract shared config loader", "status": "pending"},\n'
    '     {"id": 3, "task": "Replace inline SQL with staged models", "status": "pending"},\n'
    '     {"id": 4, "task": "Start phase 2: tests", "status": "pending"}]\n'
    "  When phase 1 wraps, collapse it and open phase 2:\n"
    '    [{"id": 1, "task": "Phase 1: refactor ingestion pipeline", "status": "completed"},\n'
    '     {"id": 2, "task": "Add unit tests for config loader", "status": "in_progress"},\n'
    '     {"id": 3, "task": "Add integration test for staged models", "status": "pending"},\n'
    '     {"id": 4, "task": "Start phase 3: wire into CI", "status": "pending"}]\n\n'
    "**Important:** call this tool on its own — don't batch with other tool calls, "
    "so the UI reflects the current state in real time."
)
