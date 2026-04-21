// Per-tool renderers.
//
// Each renderer is a React component that receives { args, result } and
// returns what to show when the tool call is expanded.
//
// To add a new tool: write a component and add it to the `renderers` map
// at the bottom. Unknown tools fall back to the raw JSON view.

import { CheckCircle2, Circle, Loader2 } from "lucide-react";

function Section({ label, children }) {
  return (
    <div className="tool-detail-section">
      <span className="tool-detail-label">{label}</span>
      {children}
    </div>
  );
}

function Code({ children }) {
  return <pre>{children}</pre>;
}

// ---- Individual tool renderers ------------------------------------------

function WriteFileView({ args }) {
  return (
    <>
      <Section label={args.path}>
        <Code>{args.content}</Code>
      </Section>
    </>
  );
}

function EditFileView({ args }) {
  const oldLines = (args.old_string || "").split("\n");
  const newLines = (args.new_string || "").split("\n");
  return (
    <Section label={args.path}>
      <div className="diff">
        {oldLines.map((line, i) => (
          <div key={`o-${i}`} className="diff-line diff-remove">
            <span className="diff-marker">-</span>
            <span>{line || "\u00A0"}</span>
          </div>
        ))}
        {newLines.map((line, i) => (
          <div key={`n-${i}`} className="diff-line diff-add">
            <span className="diff-marker">+</span>
            <span>{line || "\u00A0"}</span>
          </div>
        ))}
      </div>
    </Section>
  );
}

function ReadFileView({ args }) {
  // Just show the path — the file contents are for the agent, not the user
  return (
    <Section label="Reading">
      <code className="inline-code">{args.path}</code>
    </Section>
  );
}

function BashView({ args }) {
  return (
    <Section label="Command">
      <Code>$ {args.command}</Code>
    </Section>
  );
}

function TodosView({ args }) {
  const todos = args.todos || [];
  return (
    <Section label={`${todos.length} todos`}>
      <div className="todo-preview">
        {todos.map((t) => {
          const status = t.status ?? (t.completed ? "completed" : "pending");
          return (
            <div key={t.id} className={`todo-preview-item ${status}`}>
              {status === "completed" ? (
                <CheckCircle2 size={12} className="todo-icon completed" />
              ) : status === "in_progress" ? (
                <Loader2 size={12} className="todo-icon in_progress" />
              ) : (
                <Circle size={12} className="todo-icon" />
              )}
              <span>{t.task}</span>
            </div>
          );
        })}
      </div>
    </Section>
  );
}

function FallbackView({ args }) {
  return (
    <Section label="Input">
      <Code>{JSON.stringify(args, null, 2)}</Code>
    </Section>
  );
}

// ---- Registry ----------------------------------------------------------

const renderers = {
  Write: WriteFileView,
  Edit: EditFileView,
  Read: ReadFileView,
  bash: BashView,
  Todos: TodosView,
};

export function renderToolCall(toolCall, toolResult) {
  const View = renderers[toolCall.name] || FallbackView;
  return (
    <>
      <View args={toolCall.args} />
      {toolResult && (
        <Section label="Output">
          <Code>{toolResult.content}</Code>
        </Section>
      )}
    </>
  );
}
