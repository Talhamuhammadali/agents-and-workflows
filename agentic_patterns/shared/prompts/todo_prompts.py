"""Prompts related to todo list management."""

UPDATE_TODOS_DESCRIPTION = """\
# Update Todos

Overwrites the entire todos list in state with the provided list. Use this \
tool to track multi-step work: add items when planning, flip an item to \
`in_progress` RIGHT BEFORE you start that step, and mark it `completed` \
AS SOON AS the step is done.

## Status lifecycle

- `pending` — planned but not started.
- `in_progress` — you are actively working on it right now. Keep at most \
**ONE** item in this state at a time; it signals the current focus to the user.
- `completed` — done.

## Call rules

- **Atomic.** Every call replaces the FULL list — regenerate every todo \
each time. This is a replace, not a patch, so partial updates will drop \
items that aren't repeated.
- **Sequential.** Never invoke this tool in parallel with other tools. \
Prefer calling `Todos` on its own so the UI reflects the new state \
immediately. If you absolutely must include it in a parallel batch, it \
MUST be the **LAST** call in that batch, so the UI update lands without \
being blocked behind other tools.

## Sizing & phasing

- Keep each todo to a short one-line task — not a paragraph or a summary.
- Keep the active list to **5–6 items**. Long lists (16+) are a smell — \
you're planning at the wrong granularity.
- For complex work, break it into phases. Each phase is its own short list, \
and the last todo of a phase should point at the next phase so the handoff \
is explicit.
- When a phase completes, collapse its finished items into a single \
one-line `completed` marker (a short phase label, not a summary) so the \
history stays visible, then expand the next phase's todos below it.

## Parameters

- `todos` (list[dict]) — the complete list of todo items. Each item:
    - `id` (int) — unique identifier for the todo.
    - `task` (str) — description of what needs to be done.
    - `status` (str) — one of `pending` | `in_progress` | `completed`.

## Example

```json
[
  {"id": 1, "task": "Read config", "status": "completed"},
  {"id": 2, "task": "Parse entries", "status": "in_progress"},
  {"id": 3, "task": "Write report", "status": "pending"}
]
```

## Scenario — phased work

User asks: *"Refactor the ingestion pipeline, add tests, and wire it into \
CI."* That's three phases. Start with phase 1 only:

```json
[
  {"id": 1, "task": "Map current ingestion call sites", "status": "in_progress"},
  {"id": 2, "task": "Extract shared config loader", "status": "pending"},
  {"id": 3, "task": "Replace inline SQL with staged models", "status": "pending"},
  {"id": 4, "task": "Start phase 2: tests", "status": "pending"}
]
```

When phase 1 wraps, collapse it and open phase 2:

```json
[
  {"id": 1, "task": "Phase 1: refactor ingestion pipeline", "status": "completed"},
  {"id": 2, "task": "Add unit tests for config loader", "status": "in_progress"},
  {"id": 3, "task": "Add integration test for staged models", "status": "pending"},
  {"id": 4, "task": "Start phase 3: wire into CI", "status": "pending"}
]
```
"""
