# ruff: noqa
"""Dummy backend with hardcoded threads and messages for UI development and testing."""

from datetime import UTC, datetime

from ui.backend.models import MessageResponse

TS = "2026-04-18T10:00:00Z"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _msg(id, role, mtype, content, *, thread_id, name=None, timestamp=None):
    return MessageResponse(
        id=id,
        thread_id=thread_id,
        checkpoint_id=None,
        message_type=mtype,
        role_type=role,
        subtype=None,
        content=content,
        name=name,
        timestamp=timestamp or TS,
    )


# --- Thread 1: Quantum computing essay -----------------------------------

T1_MESSAGES = [
    _msg(
        "h-1",
        "human",
        "text",
        "Write me a short essay about quantum computing. Create the files in my workspace.",
        thread_id="t-1",
    ),
    _msg(
        "ai-1",
        "ai",
        "reasoning",
        "The user wants an essay and files created.\n\n"
        "1. Research key concepts\n"
        "2. Create the markdown file\n"
        "3. Add code examples\n\n"
        "Keep it accessible — not too technical.",
        thread_id="t-1",
        name="essay-writer",
    ),
    _msg(
        "ai-1",
        "ai",
        "text",
        "I'll write a short essay on quantum computing and set up some example files.",
        thread_id="t-1",
        name="essay-writer",
    ),
    _msg(
        "ai-1",
        "ai",
        "tool_call",
        {
            "id": "call_abc123",
            "name": "write_file",
            "type": "tool_call",
            "args": {
                "path": "quantum_intro.md",
                "content": (
                    "# Introduction to Quantum Computing\n\n"
                    "Quantum computing represents a fundamental shift in how we process information. "
                    "Unlike classical computers that use bits (0 or 1), quantum computers use qubits "
                    "that can exist in multiple states simultaneously.\n\n"
                    "## Key Concepts\n\n- Superposition\n- Entanglement\n- Quantum Gates"
                ),
            },
        },
        thread_id="t-1",
        name="essay-writer",
    ),
    _msg(
        "ai-1",
        "ai",
        "tool_call",
        {
            "id": "call_abc124",
            "name": "write_file",
            "type": "tool_call",
            "args": {
                "path": "examples/basic_qubit.py",
                "content": (
                    "from qiskit import QuantumCircuit\n\n"
                    "qc = QuantumCircuit(1, 1)\n"
                    "qc.h(0)  # Put qubit in superposition\n"
                    "qc.measure(0, 0)\n"
                    "print(qc)\n"
                ),
            },
        },
        thread_id="t-1",
        name="essay-writer",
    ),
    _msg(
        "ai-1",
        "ai",
        "tool_call",
        {
            "id": "call_abc125",
            "name": "update_todos",
            "type": "tool_call",
            "args": {
                "todos": [
                    {"id": "1", "task": "Research quantum computing basics", "completed": True},
                    {"id": "2", "task": "Write introduction section", "completed": True},
                    {"id": "3", "task": "Add code examples", "completed": False},
                    {"id": "4", "task": "Review and polish final draft", "completed": False},
                ],
            },
        },
        thread_id="t-1",
        name="essay-writer",
    ),
    _msg(
        "call_abc123",
        "tool_result",
        "tool_result",
        "File written: quantum_intro.md (420 bytes)",
        thread_id="t-1",
        name="write_file",
    ),
    _msg(
        "call_abc124",
        "tool_result",
        "tool_result",
        "File written: examples/basic_qubit.py (215 bytes)",
        thread_id="t-1",
        name="write_file",
    ),
    _msg(
        "call_abc125",
        "tool_result",
        "tool_result",
        "Todos updated. 4 item(s) in list.",
        thread_id="t-1",
        name="update_todos",
    ),
    _msg(
        "ai-2",
        "ai",
        "text",
        "Created the essay and a basic qubit example. Want me to add the entanglement example?",
        thread_id="t-1",
        name="essay-writer",
    ),
    _msg(
        "h-2",
        "human",
        "text",
        "Yes — read the intro, add the entanglement example, run it, and tighten the intro.",
        thread_id="t-1",
    ),
    _msg(
        "ai-3",
        "ai",
        "reasoning",
        "Plan:\n"
        "1. Re-read the intro so the edit diff is accurate\n"
        "2. Write the entanglement example\n"
        "3. Run it with bash\n"
        "4. Edit the intro\n"
        "5. Fetch a reference link (unknown tool — fallback JSON view)",
        thread_id="t-1",
        name="essay-writer",
    ),
    _msg("ai-3", "ai", "text", "On it.", thread_id="t-1", name="essay-writer"),
    _msg(
        "ai-3",
        "ai",
        "tool_call",
        {
            "id": "call_def455",
            "name": "read_file",
            "type": "tool_call",
            "args": {"path": "quantum_intro.md"},
        },
        thread_id="t-1",
        name="essay-writer",
    ),
    _msg(
        "ai-3",
        "ai",
        "tool_call",
        {
            "id": "call_def456",
            "name": "write_file",
            "type": "tool_call",
            "args": {
                "path": "examples/entanglement.py",
                "content": (
                    "from qiskit import QuantumCircuit\n\n"
                    "qc = QuantumCircuit(2, 2)\n"
                    "qc.h(0)\n"
                    "qc.cx(0, 1)  # Entangle qubits\n"
                    "qc.measure([0, 1], [0, 1])\n"
                    "print('Entangled circuit:')\n"
                    "print(qc)\n"
                ),
            },
        },
        thread_id="t-1",
        name="essay-writer",
    ),
    _msg(
        "ai-3",
        "ai",
        "tool_call",
        {
            "id": "call_def457",
            "name": "bash",
            "type": "tool_call",
            "args": {"command": "python examples/entanglement.py"},
        },
        thread_id="t-1",
        name="essay-writer",
    ),
    _msg(
        "ai-3",
        "ai",
        "tool_call",
        {
            "id": "call_def458",
            "name": "edit_file",
            "type": "tool_call",
            "args": {
                "path": "quantum_intro.md",
                "old_string": (
                    "Quantum computing represents a fundamental shift in how we process information. "
                    "Unlike classical computers that use bits (0 or 1), quantum computers use qubits "
                    "that can exist in multiple states simultaneously."
                ),
                "new_string": (
                    "Quantum computing uses qubits — units that hold 0, 1, or both at once — "
                    "to process information in ways classical bits cannot."
                ),
            },
        },
        thread_id="t-1",
        name="essay-writer",
    ),
    _msg(
        "ai-3",
        "ai",
        "tool_call",
        {
            "id": "call_def459",
            "name": "fetch_url",
            "type": "tool_call",
            "args": {"url": "https://example.com/quantum-refs", "format": "markdown"},
        },
        thread_id="t-1",
        name="essay-writer",
    ),
    _msg(
        "call_def455",
        "tool_result",
        "tool_result",
        "# Introduction to Quantum Computing\n\nQuantum computing represents...",
        thread_id="t-1",
        name="read_file",
    ),
    _msg(
        "call_def456",
        "tool_result",
        "tool_result",
        "File written: examples/entanglement.py (340 bytes)",
        thread_id="t-1",
        name="write_file",
    ),
    _msg(
        "call_def457",
        "tool_result",
        "tool_result",
        "Entangled circuit:\n"
        "     ┌───┐     ┌─┐   \n"
        "q_0: ┤ H ├──■──┤M├───\n"
        "     └───┘┌─┴─┐└╥┘┌─┐\n"
        "q_1: ─────┤ X ├─╫─┤M├\n"
        "          └───┘ ║ └╥┘\n",
        thread_id="t-1",
        name="bash",
    ),
    _msg(
        "call_def458", "tool_result", "tool_result", "File edited: quantum_intro.md", thread_id="t-1", name="edit_file"
    ),
    _msg(
        "call_def459",
        "tool_result",
        "tool_result",
        "Fetched 4KB of markdown from example.com/quantum-refs",
        thread_id="t-1",
        name="fetch_url",
    ),
    _msg(
        "ai-4",
        "ai",
        "text",
        "Done. The entanglement circuit ran cleanly and the intro is tightened.",
        thread_id="t-1",
        name="essay-writer",
    ),
]


# --- Thread 2: Debug a KeyError in parse.py ------------------------------

T2_MESSAGES = [
    _msg(
        "h-1",
        "human",
        "text",
        "My Python script is throwing a KeyError on parse.py. Can you take a look?",
        thread_id="t-2",
    ),
    _msg(
        "ai-1",
        "ai",
        "reasoning",
        "The user reports a KeyError in parse.py. I'll:\n"
        "1. Read parse.py to see the key being accessed\n"
        "2. Fix the incorrect key\n"
        "3. Run the tests to confirm",
        thread_id="t-2",
        name="debugger",
    ),
    _msg("ai-1", "ai", "text", "Let me take a look at parse.py.", thread_id="t-2", name="debugger"),
    _msg(
        "ai-1",
        "ai",
        "tool_call",
        {
            "id": "call_dbg1",
            "name": "read_file",
            "type": "tool_call",
            "args": {"path": "parse.py"},
        },
        thread_id="t-2",
        name="debugger",
    ),
    _msg(
        "call_dbg1",
        "tool_result",
        "tool_result",
        "def parse(row):\n    return {\n        'id': row['id'],\n        'name': row['full_name'],\n    }\n",
        thread_id="t-2",
        name="read_file",
    ),
    _msg(
        "ai-2",
        "ai",
        "text",
        "Found it — the row uses `name`, not `full_name`. I'll fix the key and run the tests.",
        thread_id="t-2",
        name="debugger",
    ),
    _msg(
        "ai-2",
        "ai",
        "tool_call",
        {
            "id": "call_dbg2",
            "name": "edit_file",
            "type": "tool_call",
            "args": {
                "path": "parse.py",
                "old_string": "'name': row['full_name'],",
                "new_string": "'name': row['name'],",
            },
        },
        thread_id="t-2",
        name="debugger",
    ),
    _msg(
        "ai-2",
        "ai",
        "tool_call",
        {
            "id": "call_dbg3",
            "name": "bash",
            "type": "tool_call",
            "args": {"command": "python -m pytest tests/test_parse.py -v"},
        },
        thread_id="t-2",
        name="debugger",
    ),
    _msg("call_dbg2", "tool_result", "tool_result", "File edited: parse.py", thread_id="t-2", name="edit_file"),
    _msg(
        "call_dbg3",
        "tool_result",
        "tool_result",
        "===== test session starts =====\n"
        "tests/test_parse.py::test_basic PASSED\n"
        "tests/test_parse.py::test_empty PASSED\n\n"
        "===== 2 passed in 0.12s =====\n",
        thread_id="t-2",
        name="bash",
    ),
    _msg(
        "ai-3",
        "ai",
        "text",
        "Fixed. The column was `name`, not `full_name`. Tests pass.",
        thread_id="t-2",
        name="debugger",
    ),
]


THREADS: dict[str, dict] = {
    "t-1": {
        "thread_id": "t-1",
        "title": "Quantum computing essay",
        "updated_at": TS,
        "messages": T1_MESSAGES,
        "todos": [
            {"id": "1", "task": "Research quantum computing basics", "completed": True},
            {"id": "2", "task": "Write introduction section", "completed": True},
            {"id": "3", "task": "Add code examples", "completed": False},
            {"id": "4", "task": "Review and polish final draft", "completed": False},
        ],
        "workspace": [
            {"name": "quantum_intro.md", "type": "file"},
            {"name": "examples/", "type": "folder"},
            {"name": "examples/basic_qubit.py", "type": "file"},
            {"name": "examples/entanglement.py", "type": "file"},
            {"name": "notes.txt", "type": "file"},
        ],
        "artifact": {
            "title": "quantum_intro.md",
            "language": "markdown",
            "content": (
                "# Introduction to Quantum Computing\n\n"
                "Quantum computing uses qubits — units that hold 0, 1, or both at once —\n"
                "to process information in ways classical bits cannot.\n\n"
                "## Key Concepts\n\n"
                "### Superposition\nA qubit can be in a state of 0, 1, or both at the same time.\n\n"
                "### Entanglement\nWhen two qubits become entangled, measuring one instantly affects the other.\n\n"
                "### Quantum Gates\nLike classical logic gates, quantum gates manipulate qubits.\n"
            ),
        },
    },
    "t-2": {
        "thread_id": "t-2",
        "title": "Debug KeyError in parse.py",
        "updated_at": TS,
        "messages": T2_MESSAGES,
        "todos": [],
        "workspace": [
            {"name": "parse.py", "type": "file"},
            {"name": "tests/", "type": "folder"},
            {"name": "tests/test_parse.py", "type": "file"},
        ],
        "artifact": {
            "title": "parse.py",
            "language": "python",
            "content": (
                "def parse(row):\n    return {\n        'id': row['id'],\n        'name': row['name'],\n    }\n"
            ),
        },
    },
}
