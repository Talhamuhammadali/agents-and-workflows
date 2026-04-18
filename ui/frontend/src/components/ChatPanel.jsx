import { useState } from "react";
import { Send } from "lucide-react";
import HumanMessage from "./HumanMessage";
import AIMessage from "./AIMessage";
import TodoSection from "./TodoSection";

export default function ChatPanel({
  threads,
  activeThreadId,
  onSelectThread,
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
          <button
            key={t.thread_id}
            className={`thread-tab ${t.thread_id === activeThreadId ? "active" : ""}`}
            onClick={() => onSelectThread(t.thread_id)}
          >
            {t.title}
          </button>
        ))}
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
