import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { Maximize2, Minimize2, Pause, Plus, Send, X } from "lucide-react";
import HumanMessage from "./HumanMessage";
import AIMessage from "./AIMessage";
import TodoSection from "./TodoSection";
import QuestionCard from "./QuestionCard";

export default function ChatPanel({
  threads,
  activeThreadId,
  onSelectThread,
  onNewThread,
  onDeleteThread,
  messages,
  todos,
  pendingInterrupts,
  onSend,
  onInterrupt,
  sending,
  chatWidth,
  onChatWidthChange,
}) {
  const hasPending = (pendingInterrupts?.length ?? 0) > 0;
  const [input, setInput] = useState("");
  const [expanded, setExpanded] = useState(false);
  const textareaRef = useRef(null);

  useLayoutEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "";
    el.style.height = `${el.scrollHeight}px`;
  }, [input, expanded]);

  // Esc interrupts the active stream. Global listener because the textarea is
  // disabled during streaming and can't catch keys itself.
  useEffect(() => {
    if (!sending || !onInterrupt) return;
    function onKey(e) {
      if (e.key === "Escape") {
        e.preventDefault();
        onInterrupt();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [sending, onInterrupt]);

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

  // Drag the left edge of the panel to resize the column width. Moving the
  // pointer LEFT grows the chat (startX - clientX > 0); RIGHT shrinks it.
  function onResizerPointerDown(e) {
    if (!onChatWidthChange) return;
    e.preventDefault();
    const startX = e.clientX;
    const startWidth = chatWidth;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    function onMove(ev) {
      const next = Math.min(
        Math.max(320, startWidth + (startX - ev.clientX)),
        Math.floor(window.innerWidth * 0.7)
      );
      onChatWidthChange(next);
    }
    function onUp() {
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
    }
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
  }

  return (
    <div className="chat-panel">
      <div
        className="chat-resizer"
        onPointerDown={onResizerPointerDown}
        title="Drag to resize"
      />
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
        {hasPending ? (
          <QuestionCard
            pendingInterrupts={pendingInterrupts}
            onSubmit={(resumeMap) => onSend(resumeMap)}
          />
        ) : (
          <div className="chat-input-card">
            <textarea
              ref={textareaRef}
              className={expanded ? "expanded" : ""}
              rows={1}
              placeholder={sending ? "Streaming…" : "Type a message... (Shift+Enter for new line)"}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  submit();
                }
              }}
              disabled={sending}
            />
            <div className="chat-input-actions">
              <button
                type="button"
                className="expand-btn"
                onClick={() => setExpanded((v) => !v)}
                title={expanded ? "Collapse" : "Expand"}
              >
                {expanded ? <Minimize2 size={13} /> : <Maximize2 size={13} />}
              </button>
              <div className="chat-input-actions-right">
                <button
                  type="button"
                  className="interrupt-btn"
                  onClick={onInterrupt}
                  disabled={!sending}
                  title="Stop (Esc)"
                >
                  <Pause size={14} />
                </button>
                <button
                  className="send-btn"
                  onClick={submit}
                  disabled={sending || !input.trim()}
                  title="Send (Enter)"
                >
                  <Send size={14} />
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
