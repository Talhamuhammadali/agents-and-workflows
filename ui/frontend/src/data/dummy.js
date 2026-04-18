// Dummy data matching the backend MessageResponse[] shape.
// The UI accumulator (same semantics as docs/sse-streaming.md) groups
// events with the same `id` into a single AI bubble; `tool_result` items
// link back to their originating tool_call via matching `id`.

// Non-message panels (workspace file tree, todos, artifact preview) stay
// as top-level fields for now — they're UI state, not chat history.

const TS = "2026-04-18T10:00:00Z";

const messages = [
  // --- Turn 1: user asks for the essay ----------------------------------
  {
    id: "h-1", thread_id: "t-1", checkpoint_id: null,
    message_type: "text", role_type: "human", subtype: null,
    content: "Write me a short essay about quantum computing. Create the files in my workspace.",
    name: null, timestamp: TS,
  },

  // AI turn (merge key: ai-1)
  {
    id: "ai-1", thread_id: "t-1", checkpoint_id: null,
    message_type: "reasoning", role_type: "ai", subtype: null,
    content:
      "The user wants an essay and files created.\n\n" +
      "1. Research key concepts\n" +
      "2. Create the markdown file\n" +
      "3. Add code examples\n\n" +
      "Keep it accessible — not too technical.",
    name: "essay-writer", timestamp: TS,
  },
  {
    id: "ai-1", thread_id: "t-1", checkpoint_id: null,
    message_type: "text", role_type: "ai", subtype: null,
    content: "I'll write a short essay on quantum computing and set up some example files.",
    name: "essay-writer", timestamp: TS,
  },
  {
    id: "ai-1", thread_id: "t-1", checkpoint_id: null,
    message_type: "tool_call", role_type: "ai", subtype: null,
    content: {
      id: "call_abc123", name: "write_file", type: "tool_call",
      args: {
        path: "quantum_intro.md",
        content:
          "# Introduction to Quantum Computing\n\n" +
          "Quantum computing represents a fundamental shift in how we process information. " +
          "Unlike classical computers that use bits (0 or 1), quantum computers use qubits " +
          "that can exist in multiple states simultaneously.\n\n" +
          "## Key Concepts\n\n- Superposition\n- Entanglement\n- Quantum Gates",
      },
    },
    name: "essay-writer", timestamp: TS,
  },
  {
    id: "ai-1", thread_id: "t-1", checkpoint_id: null,
    message_type: "tool_call", role_type: "ai", subtype: null,
    content: {
      id: "call_abc124", name: "write_file", type: "tool_call",
      args: {
        path: "examples/basic_qubit.py",
        content:
          "from qiskit import QuantumCircuit\n\n" +
          "qc = QuantumCircuit(1, 1)\n" +
          "qc.h(0)  # Put qubit in superposition\n" +
          "qc.measure(0, 0)\n" +
          "print(qc)\n",
      },
    },
    name: "essay-writer", timestamp: TS,
  },
  {
    id: "ai-1", thread_id: "t-1", checkpoint_id: null,
    message_type: "tool_call", role_type: "ai", subtype: null,
    content: {
      id: "call_abc125", name: "update_todos", type: "tool_call",
      args: {
        todos: [
          { id: "1", task: "Research quantum computing basics", completed: true },
          { id: "2", task: "Write introduction section", completed: true },
          { id: "3", task: "Add code examples", completed: false },
          { id: "4", task: "Review and polish final draft", completed: false },
        ],
      },
    },
    name: "essay-writer", timestamp: TS,
  },

  // tool results — id equals the originating tool_call.id
  {
    id: "call_abc123", thread_id: "t-1", checkpoint_id: null,
    message_type: "tool_result", role_type: "tool_result", subtype: null,
    content: "File written: quantum_intro.md (420 bytes)",
    name: "write_file", timestamp: TS,
  },
  {
    id: "call_abc124", thread_id: "t-1", checkpoint_id: null,
    message_type: "tool_result", role_type: "tool_result", subtype: null,
    content: "File written: examples/basic_qubit.py (215 bytes)",
    name: "write_file", timestamp: TS,
  },
  {
    id: "call_abc125", thread_id: "t-1", checkpoint_id: null,
    message_type: "tool_result", role_type: "tool_result", subtype: null,
    content: "Todos updated. 4 item(s) in list.",
    name: "update_todos", timestamp: TS,
  },

  // AI wrap-up turn (new merge key: ai-2)
  {
    id: "ai-2", thread_id: "t-1", checkpoint_id: null,
    message_type: "text", role_type: "ai", subtype: null,
    content: "Created the essay and a basic qubit example. Want me to add the entanglement example?",
    name: "essay-writer", timestamp: TS,
  },

  // --- Turn 2: user follow-up covering the rest of the tool renderers ---
  {
    id: "h-2", thread_id: "t-1", checkpoint_id: null,
    message_type: "text", role_type: "human", subtype: null,
    content: "Yes — read the intro, add the entanglement example, run it, and tighten the intro.",
    name: null, timestamp: TS,
  },

  // AI turn (merge key: ai-3) — exercises read_file, write_file, bash, edit_file, and an unknown tool (fallback)
  {
    id: "ai-3", thread_id: "t-1", checkpoint_id: null,
    message_type: "reasoning", role_type: "ai", subtype: null,
    content:
      "Plan:\n" +
      "1. Re-read the intro so the edit diff is accurate\n" +
      "2. Write the entanglement example\n" +
      "3. Run it with bash\n" +
      "4. Edit the intro\n" +
      "5. Fetch a reference link to cite (unknown tool — falls through to the JSON view)",
    name: "essay-writer", timestamp: TS,
  },
  {
    id: "ai-3", thread_id: "t-1", checkpoint_id: null,
    message_type: "text", role_type: "ai", subtype: null,
    content: "On it.",
    name: "essay-writer", timestamp: TS,
  },
  {
    id: "ai-3", thread_id: "t-1", checkpoint_id: null,
    message_type: "tool_call", role_type: "ai", subtype: null,
    content: {
      id: "call_def455", name: "read_file", type: "tool_call",
      args: { path: "quantum_intro.md" },
    },
    name: "essay-writer", timestamp: TS,
  },
  {
    id: "ai-3", thread_id: "t-1", checkpoint_id: null,
    message_type: "tool_call", role_type: "ai", subtype: null,
    content: {
      id: "call_def456", name: "write_file", type: "tool_call",
      args: {
        path: "examples/entanglement.py",
        content:
          "from qiskit import QuantumCircuit\n\n" +
          "qc = QuantumCircuit(2, 2)\n" +
          "qc.h(0)\n" +
          "qc.cx(0, 1)  # Entangle qubits\n" +
          "qc.measure([0, 1], [0, 1])\n" +
          "print('Entangled circuit:')\n" +
          "print(qc)\n",
      },
    },
    name: "essay-writer", timestamp: TS,
  },
  {
    id: "ai-3", thread_id: "t-1", checkpoint_id: null,
    message_type: "tool_call", role_type: "ai", subtype: null,
    content: {
      id: "call_def457", name: "bash", type: "tool_call",
      args: { command: "python examples/entanglement.py" },
    },
    name: "essay-writer", timestamp: TS,
  },
  {
    id: "ai-3", thread_id: "t-1", checkpoint_id: null,
    message_type: "tool_call", role_type: "ai", subtype: null,
    content: {
      id: "call_def458", name: "edit_file", type: "tool_call",
      args: {
        path: "quantum_intro.md",
        old_string:
          "Quantum computing represents a fundamental shift in how we process information. " +
          "Unlike classical computers that use bits (0 or 1), quantum computers use qubits " +
          "that can exist in multiple states simultaneously.",
        new_string:
          "Quantum computing uses qubits — units that hold 0, 1, or both at once — " +
          "to process information in ways classical bits cannot.",
      },
    },
    name: "essay-writer", timestamp: TS,
  },
  {
    // unknown tool — exercises FallbackView
    id: "ai-3", thread_id: "t-1", checkpoint_id: null,
    message_type: "tool_call", role_type: "ai", subtype: null,
    content: {
      id: "call_def459", name: "fetch_url", type: "tool_call",
      args: { url: "https://example.com/quantum-refs", format: "markdown" },
    },
    name: "essay-writer", timestamp: TS,
  },

  // tool results
  {
    id: "call_def455", thread_id: "t-1", checkpoint_id: null,
    message_type: "tool_result", role_type: "tool_result", subtype: null,
    content: "# Introduction to Quantum Computing\n\nQuantum computing represents...",
    name: "read_file", timestamp: TS,
  },
  {
    id: "call_def456", thread_id: "t-1", checkpoint_id: null,
    message_type: "tool_result", role_type: "tool_result", subtype: null,
    content: "File written: examples/entanglement.py (340 bytes)",
    name: "write_file", timestamp: TS,
  },
  {
    id: "call_def457", thread_id: "t-1", checkpoint_id: null,
    message_type: "tool_result", role_type: "tool_result", subtype: null,
    content:
      "Entangled circuit:\n" +
      "     ┌───┐     ┌─┐   \n" +
      "q_0: ┤ H ├──■──┤M├───\n" +
      "     └───┘┌─┴─┐└╥┘┌─┐\n" +
      "q_1: ─────┤ X ├─╫─┤M├\n" +
      "          └───┘ ║ └╥┘\n",
    name: "bash", timestamp: TS,
  },
  {
    id: "call_def458", thread_id: "t-1", checkpoint_id: null,
    message_type: "tool_result", role_type: "tool_result", subtype: null,
    content: "File edited: quantum_intro.md",
    name: "edit_file", timestamp: TS,
  },
  {
    id: "call_def459", thread_id: "t-1", checkpoint_id: null,
    message_type: "tool_result", role_type: "tool_result", subtype: null,
    content: "Fetched 4KB of markdown from example.com/quantum-refs",
    name: "fetch_url", timestamp: TS,
  },

  // AI wrap-up (merge key: ai-4)
  {
    id: "ai-4", thread_id: "t-1", checkpoint_id: null,
    message_type: "text", role_type: "ai", subtype: null,
    content: "Done. The entanglement circuit ran cleanly and the intro is tightened.",
    name: "essay-writer", timestamp: TS,
  },
];

const conversation = {
  messages,

  // UI-only panel state (not part of the chat stream).
  // Open question: should these arrive as `notification` events and get
  // folded into client state, or stay as separate history endpoints?
  todos: [
    { id: "1", task: "Research quantum computing basics", completed: true },
    { id: "2", task: "Write introduction section", completed: true },
    { id: "3", task: "Add code examples", completed: false },
    { id: "4", task: "Review and polish final draft", completed: false },
  ],
  workspace: [
    { name: "quantum_intro.md", type: "file" },
    { name: "examples/", type: "folder" },
    { name: "examples/basic_qubit.py", type: "file" },
    { name: "examples/entanglement.py", type: "file" },
    { name: "notes.txt", type: "file" },
  ],
  artifact: {
    title: "quantum_intro.md",
    language: "markdown",
    content:
      "# Introduction to Quantum Computing\n\n" +
      "Quantum computing uses qubits — units that hold 0, 1, or both at once —\n" +
      "to process information in ways classical bits cannot.\n\n" +
      "## Key Concepts\n\n" +
      "### Superposition\nA qubit can be in a state of 0, 1, or both at the same time.\n\n" +
      "### Entanglement\nWhen two qubits become entangled, measuring one instantly affects the other.\n\n" +
      "### Quantum Gates\nLike classical logic gates, quantum gates manipulate qubits.\n",
  },
};

export default conversation;
