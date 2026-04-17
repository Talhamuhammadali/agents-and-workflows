// Dummy conversation data matching LangChain/LangGraph message format
const conversation = {
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

  messages: [
    // --- Turn 1 ---
    {
      type: "human",
      content: "Write me a short essay about quantum computing. Create the files in my workspace.",
    },
    {
      type: "ai",
      name: "essay-writer",
      content_blocks: [
        {
          type: "reasoning",
          reasoning:
            "The user wants an essay about quantum computing and wants files created.\n\n" +
            "1. First I'll research the key concepts to cover\n" +
            "2. Then create the markdown file with the essay\n" +
            "3. Add some code examples to illustrate concepts\n\n" +
            "I should keep it accessible — not too technical, but accurate.",
        },
        {
          type: "text",
          text: "I'll write a short essay on quantum computing and set up some example files for you. Let me start by creating the workspace structure.",
        },
      ],
      tool_calls: [
        {
          name: "write_file",
          args: {
            path: "quantum_intro.md",
            content:
              "# Introduction to Quantum Computing\n\n" +
              "Quantum computing represents a fundamental shift in how we process information. " +
              "Unlike classical computers that use bits (0 or 1), quantum computers use qubits " +
              "that can exist in multiple states simultaneously.\n\n" +
              "## Key Concepts\n\n" +
              "- Superposition\n- Entanglement\n- Quantum Gates",
          },
          id: "call_abc123",
          type: "tool_call",
        },
        {
          name: "write_file",
          args: {
            path: "examples/basic_qubit.py",
            content:
              "from qiskit import QuantumCircuit\n\n" +
              "qc = QuantumCircuit(1, 1)\n" +
              "qc.h(0)  # Put qubit in superposition\n" +
              "qc.measure(0, 0)\n" +
              "print(qc)\n",
          },
          id: "call_abc124",
          type: "tool_call",
        },
        {
          name: "update_todos",
          args: {
            todos: [
              { id: "1", task: "Research quantum computing basics", completed: true },
              { id: "2", task: "Write introduction section", completed: true },
              { id: "3", task: "Add code examples", completed: false },
              { id: "4", task: "Review and polish final draft", completed: false },
            ],
          },
          id: "call_abc125",
          type: "tool_call",
        },
      ],
    },
    { type: "tool", content: "File written: quantum_intro.md (420 bytes)", tool_call_id: "call_abc123", name: "write_file" },
    { type: "tool", content: "File written: examples/basic_qubit.py (215 bytes)", tool_call_id: "call_abc124", name: "write_file" },
    { type: "tool", content: "Todos updated. 4 item(s) in list.", tool_call_id: "call_abc125", name: "update_todos" },
    {
      type: "ai",
      name: "essay-writer",
      content_blocks: [
        {
          type: "text",
          text: "I've created the essay and a basic qubit example. Ready to add the entanglement example and review — want me to continue?",
        },
      ],
      tool_calls: [],
    },
    // --- Turn 2: edit_file + bash demo ---
    {
      type: "human",
      content: "Yes, add the entanglement example, run it, and tighten up the intro paragraph.",
    },
    {
      type: "ai",
      name: "essay-writer",
      content_blocks: [
        {
          type: "reasoning",
          reasoning:
            "I'll:\n" +
            "1. Create the entanglement example\n" +
            "2. Run it to verify it works\n" +
            "3. Edit the intro paragraph to make it tighter",
        },
        {
          type: "text",
          text: "On it.",
        },
      ],
      tool_calls: [
        {
          name: "write_file",
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
          id: "call_def456",
          type: "tool_call",
        },
        {
          name: "bash",
          args: { command: "python examples/entanglement.py" },
          id: "call_def457",
          type: "tool_call",
        },
        {
          name: "edit_file",
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
          id: "call_def458",
          type: "tool_call",
        },
      ],
    },
    { type: "tool", content: "File written: examples/entanglement.py (340 bytes)", tool_call_id: "call_def456", name: "write_file" },
    {
      type: "tool",
      content:
        "Entangled circuit:\n" +
        "     ┌───┐     ┌─┐   \n" +
        "q_0: ┤ H ├──■──┤M├───\n" +
        "     └───┘┌─┴─┐└╥┘┌─┐\n" +
        "q_1: ─────┤ X ├─╫─┤M├\n" +
        "          └───┘ ║ └╥┘\n",
      tool_call_id: "call_def457",
      name: "bash",
    },
    { type: "tool", content: "File edited: quantum_intro.md", tool_call_id: "call_def458", name: "edit_file" },
    {
      type: "ai",
      name: "essay-writer",
      content_blocks: [
        {
          type: "text",
          text: "Done. The entanglement circuit ran cleanly, and I tightened the intro paragraph.",
        },
      ],
      tool_calls: [],
    },
  ],

  artifact: {
    title: "quantum_intro.md",
    language: "markdown",
    content: `# Introduction to Quantum Computing

Quantum computing uses qubits — units that hold 0, 1, or both at once —
to process information in ways classical bits cannot.

## Key Concepts

### Superposition
A qubit can be in a state of 0, 1, or both at the same time.

### Entanglement
When two qubits become entangled, measuring one instantly affects the other.

### Quantum Gates
Like classical logic gates, quantum gates manipulate qubits.

## Applications

- **Cryptography**: Breaking and creating unbreakable encryption
- **Drug Discovery**: Simulating molecular interactions
- **Optimization**: Solving complex logistics problems
- **Machine Learning**: Faster training of AI models`,
  },
};

export default conversation;
