import { useState } from "react";
import { CheckCircle2, ChevronDown, ChevronRight, Circle, Loader2 } from "lucide-react";

function statusOf(todo) {
  // Tolerate legacy {completed: bool} todos persisted before the status field existed.
  if (todo.status) return todo.status;
  return todo.completed ? "completed" : "pending";
}

export default function TodoSection({ todos }) {
  const [collapsed, setCollapsed] = useState(false);
  if (!todos || todos.length === 0) return null;

  const done = todos.filter((t) => statusOf(t) === "completed").length;

  return (
    <div className="todo-section">
      <button
        type="button"
        className="todo-header"
        onClick={() => setCollapsed((v) => !v)}
        aria-expanded={!collapsed}
      >
        <span className="todo-label">
          {collapsed ? <ChevronRight size={12} /> : <ChevronDown size={12} />}
          Tasks
        </span>
        <span className="todo-count">
          {done}/{todos.length}
        </span>
      </button>
      {!collapsed && (
        <div className="todo-list">
          {todos.map((todo) => {
            const status = statusOf(todo);
            return (
              <div key={todo.id} className={`todo-item ${status}`}>
                {status === "completed" ? (
                  <CheckCircle2 size={14} className="todo-icon completed" />
                ) : status === "in_progress" ? (
                  <Loader2 size={14} className="todo-icon in_progress" />
                ) : (
                  <Circle size={14} className="todo-icon" />
                )}
                <span>{todo.task}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
