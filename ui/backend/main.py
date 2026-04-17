"""Simple FastAPI backend serving dummy agent conversation data."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Dummy data matching LangChain/LangGraph message format
# AIMessage has: content_blocks (list of thinking/reasoning/text blocks)
#                tool_calls (list of {name, args, id, type})
# ToolMessage has: content (str), tool_call_id, name
DUMMY_CONVERSATION = {
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
    "messages": [
        # --- Turn 1 ---
        {
            "type": "human",
            "content": "Write me a short essay about quantum computing. Create the files in my workspace.",
        },
        {
            "type": "ai",
            "name": "essay-writer",
            "content_blocks": [
                {
                    "type": "reasoning",
                    "reasoning": (
                        "The user wants an essay about quantum computing and wants files created. "
                        "Let me break this down:\n\n"
                        "1. First I'll research the key concepts to cover\n"
                        "2. Then create the markdown file with the essay\n"
                        "3. Add some code examples to illustrate concepts\n\n"
                        "I should keep it accessible — not too technical, but accurate."
                    ),
                },
                {
                    "type": "text",
                    "text": (
                        "I'll write a short essay on quantum computing and set up some example files "
                        "for you. Let me start by creating the workspace structure."
                    ),
                },
            ],
            "tool_calls": [
                {
                    "name": "write_file",
                    "args": {"path": "quantum_intro.md", "content": "# Introduction to Quantum Computing\n..."},
                    "id": "call_abc123",
                    "type": "tool_call",
                },
                {
                    "name": "write_file",
                    "args": {"path": "examples/basic_qubit.py", "content": "# Basic qubit example\n..."},
                    "id": "call_abc124",
                    "type": "tool_call",
                },
                {
                    "name": "update_todos",
                    "args": {
                        "todos": [
                            {"id": "1", "task": "Research quantum computing basics", "completed": True},
                            {"id": "2", "task": "Write introduction section", "completed": True},
                            {"id": "3", "task": "Add code examples", "completed": False},
                            {"id": "4", "task": "Review and polish final draft", "completed": False},
                        ]
                    },
                    "id": "call_abc125",
                    "type": "tool_call",
                },
            ],
        },
        # Tool results
        {
            "type": "tool",
            "content": "File written: quantum_intro.md (420 bytes)",
            "tool_call_id": "call_abc123",
            "name": "write_file",
        },
        {
            "type": "tool",
            "content": "File written: examples/basic_qubit.py (215 bytes)",
            "tool_call_id": "call_abc124",
            "name": "write_file",
        },
        {
            "type": "tool",
            "content": "Todos updated. 4 item(s) in list.",
            "tool_call_id": "call_abc125",
            "name": "update_todos",
        },
        # AI follow-up after tool results
        {
            "type": "ai",
            "name": "essay-writer",
            "content_blocks": [
                {
                    "type": "text",
                    "text": (
                        "I've created the essay file and a basic qubit example. The essay covers:\n\n"
                        "- What quantum computing is\n"
                        "- Key concepts: superposition, entanglement, quantum gates\n"
                        "- Current applications and future potential\n\n"
                        "I've also updated the todo list to track our progress. "
                        "I still need to add more code examples and do a final review. "
                        "Want me to continue with the entanglement example?"
                    ),
                },
            ],
            "tool_calls": [],
        },
        # --- Turn 2 ---
        {
            "type": "human",
            "content": "Yes, add the entanglement example and then review everything.",
        },
        {
            "type": "ai",
            "name": "essay-writer",
            "content_blocks": [
                {
                    "type": "reasoning",
                    "reasoning": (
                        "The user wants me to continue. I need to:\n"
                        "1. Create the entanglement example file\n"
                        "2. Review the essay for accuracy and polish\n"
                        "3. Update the todos to reflect completion"
                    ),
                },
                {
                    "type": "text",
                    "text": "On it — I'll create the entanglement example and then review the full essay.",
                },
            ],
            "tool_calls": [
                {
                    "name": "write_file",
                    "args": {
                        "path": "examples/entanglement.py",
                        "content": "# Quantum entanglement demo\nfrom qiskit import QuantumCircuit\n...",
                    },
                    "id": "call_def456",
                    "type": "tool_call",
                },
                {
                    "name": "read_file",
                    "args": {"path": "quantum_intro.md"},
                    "id": "call_def457",
                    "type": "tool_call",
                },
            ],
        },
        {
            "type": "tool",
            "content": "File written: examples/entanglement.py (340 bytes)",
            "tool_call_id": "call_def456",
            "name": "write_file",
        },
        {
            "type": "tool",
            "content": "# Introduction to Quantum Computing\n\nQuantum computing represents...",
            "tool_call_id": "call_def457",
            "name": "read_file",
        },
        {
            "type": "ai",
            "name": "essay-writer",
            "content_blocks": [
                {
                    "type": "text",
                    "text": (
                        "Done! I've added the entanglement example and reviewed the essay. "
                        "Everything looks good — the examples complement the essay well. "
                        "All tasks are now complete."
                    ),
                },
            ],
            "tool_calls": [],
        },
    ],
    "artifact": {
        "title": "quantum_intro.md",
        "language": "markdown",
        "content": (
            "# Introduction to Quantum Computing\n\n"
            "Quantum computing represents a fundamental shift in how we process information. "
            "Unlike classical computers that use bits (0 or 1), quantum computers use **qubits** "
            "that can exist in multiple states simultaneously.\n\n"
            "## Key Concepts\n\n"
            "### Superposition\n"
            "A qubit can be in a state of 0, 1, or both at the same time. "
            "This allows quantum computers to explore many solutions in parallel.\n\n"
            "### Entanglement\n"
            "When two qubits become entangled, measuring one instantly affects the other, "
            "regardless of distance. This enables powerful correlations in computation.\n\n"
            "### Quantum Gates\n"
            "Like classical logic gates, quantum gates manipulate qubits. "
            "Common gates include the Hadamard gate (creates superposition) "
            "and CNOT gate (creates entanglement).\n\n"
            "## Applications\n\n"
            "- **Cryptography**: Breaking and creating unbreakable encryption\n"
            "- **Drug Discovery**: Simulating molecular interactions\n"
            "- **Optimization**: Solving complex logistics problems\n"
            "- **Machine Learning**: Faster training of AI models\n\n"
            "## The Future\n\n"
            "While still in early stages, quantum computing promises to solve problems "
            "that would take classical computers millions of years."
        ),
    },
}


@app.get("/api/conversation")
def get_conversation():
    return DUMMY_CONVERSATION
