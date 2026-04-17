import { CheckCircle2, Circle } from "lucide-react";

export default function TodoSection({ todos }) {
  if (!todos || todos.length === 0) return null;

  const done = todos.filter((t) => t.completed).length;

  return (
    <div className="todo-section">
      <div className="todo-header">
        <span className="todo-label">Tasks</span>
        <span className="todo-count">
          {done}/{todos.length}
        </span>
      </div>
      <div className="todo-list">
        {todos.map((todo) => (
          <div
            key={todo.id}
            className={`todo-item ${todo.completed ? "done" : ""}`}
          >
            {todo.completed ? (
              <CheckCircle2 size={14} className="todo-icon done" />
            ) : (
              <Circle size={14} className="todo-icon" />
            )}
            <span>{todo.task}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
