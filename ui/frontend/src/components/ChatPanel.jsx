import { useState } from "react";
import { Plus, Send, X } from "lucide-react";
import HumanMessage from "./HumanMessage";
import AIMessage from "./AIMessage";
import TodoSection from "./TodoSection";

export default function ChatPanel({
  threads,
  activeThreadId,
  onSelectThread,
  onNewThread,
  onDeleteThread,
  messages,
  todos,
  onSend,
  sending,
}) {
  const [input, setInput] = useState("");

  // Only render human and ai messages (tool messages are shown inside AIMessage)
  const visibleMessages = messages.filter(
    (m) => m.type === "human" || m.type === "ai"
  );

  // Index of the last AI message — used to auto-expand its live tool call.
  let lastAiIndex = -1;
  for (let i = visibleMessages.length - 1; i >= 0; i--) {
    if (visibleMessages[i].type === "ai") {
      lastAiIndex = i;
      break;
    }
  }

  function submit() {
    const text = input.trim();
    if (!text || sending) return;
    setInput("");
    onSend(text);
  }

  return (
    <div className="chat-panel">
      <div className="chat-header thread-tabs">
        {threads.map((t) => (
          <div
            key={t.thread_id}
            className={`thread-tab ${t.thread_id === activeThreadId ? "active" : ""}`}
            onClick={() => onSelectThread(t.thread_id)}
            role="button"
          >
            <span className="thread-tab-title">{t.title}</span>
            <button
              className="thread-tab-close"
              title="Delete chat"
              onClick={(e) => {
                e.stopPropagation();
                onDeleteThread?.(t.thread_id);
              }}
            >
              <X size={12} />
            </button>
          </div>
        ))}
        <button
          className="thread-tab new-thread-btn"
          onClick={onNewThread}
          title="New chat"
          disabled={sending}
        >
          <Plus size={14} />
          New
        </button>
      </div>

      <div className="chat-messages">
        {visibleMessages.map((msg, i) => {
          const originalIndex = messages.indexOf(msg);
          if (msg.type === "human") {
            return <HumanMessage key={i} message={msg} />;
          }
          return (
            <AIMessage
              key={i}
              message={msg}
              allMessages={messages}
              messageIndex={originalIndex}
              isLive={sending && i === lastAiIndex}
            />
          );
        })}
      </div>

      <TodoSection todos={todos} />

      <div className="chat-input">
        <input
          type="text"
          placeholder={sending ? "Streaming…" : "Type a message..."}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
          disabled={sending}
        />
        <button className="send-btn" onClick={submit} disabled={sending || !input.trim()}>
          <Send size={16} />
        </button>
      </div>
    </div>
  );
}
