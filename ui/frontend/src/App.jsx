import { useEffect, useMemo, useRef, useState } from "react";
import { accumulate } from "./stream/accumulator";
import { streamPost } from "./stream/postStream";
import Sidebar from "./components/Sidebar";
import ArtifactPanel from "./components/ArtifactPanel";
import ChatPanel from "./components/ChatPanel";
import "./App.css";

const EMPTY_BUNDLE = { events: [], todos: [], workspace: [], artifact: null };

async function createThread(title) {
  const res = await fetch("/api/threads", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title: title ?? null }),
  });
  if (!res.ok) throw new Error(`Create thread failed: ${res.status}`);
  return res.json();
}

export default function App() {
  const [threads, setThreads] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [bundle, setBundle] = useState(EMPTY_BUNDLE);
  const [sending, setSending] = useState(false);
  const [chatWidth, setChatWidth] = useState(420);

  const messages = useMemo(() => accumulate(bundle.events), [bundle.events]);
  const didInit = useRef(false);

  // Load thread list on mount. If empty, create a fresh thread on the server.
  // Guarded against StrictMode's double-invoke so we don't POST twice.
  useEffect(() => {
    if (didInit.current) return;
    didInit.current = true;
    fetch("/api/threads")
      .then((r) => r.json())
      .then(async (ts) => {
        if (ts.length === 0) {
          const fresh = await createThread();
          setThreads([fresh]);
          setActiveId(fresh.thread_id);
        } else {
          setThreads(ts);
          setActiveId(ts[0].thread_id);
        }
      })
      .catch((err) => console.error("Failed to load threads:", err));
  }, []);

  async function handleNewThread() {
    try {
      const fresh = await createThread();
      setThreads((prev) => [fresh, ...prev]);
      setActiveId(fresh.thread_id);
      setBundle(EMPTY_BUNDLE);
    } catch (err) {
      console.error("Failed to create thread:", err);
    }
  }

  async function handleDeleteThread(threadId) {
    try {
      const res = await fetch(`/api/threads/${threadId}`, { method: "DELETE" });
      if (!res.ok) throw new Error(`Delete failed: ${res.status}`);
      setThreads((prev) => {
        const next = prev.filter((t) => t.thread_id !== threadId);
        if (threadId === activeId) {
          const fallback = next[0]?.thread_id ?? null;
          setActiveId(fallback);
          if (!fallback) setBundle(EMPTY_BUNDLE);
        }
        return next;
      });
    } catch (err) {
      console.error("Failed to delete thread:", err);
    }
  }

  // Load messages + panel state in parallel whenever the active thread changes.
  useEffect(() => {
    if (!activeId) return;
    // Thread context changed — any in-flight stream belongs to the old thread,
    // so clear `sending` so this thread's input is usable.
    setSending(false);
    Promise.all([
      fetch(`/api/threads/${activeId}`).then((r) => r.json()),
      fetch(`/api/threads/${activeId}/state`).then((r) => r.json()),
    ])
      .then(([thread, state]) =>
        setBundle({
          events: thread.messages,
          todos: state.todos,
          workspace: state.workspace,
          artifact: state.artifact,
        })
      )
      .catch((err) => console.error("Failed to load thread:", err));
  }, [activeId]);

  async function handleSend(message) {
    // Stream only emits AI/tool events — add the human turn optimistically so
    // the user's message is visible immediately and survives through the turn.
    const humanEvent = {
      id: `local-${Date.now()}`,
      thread_id: activeId,
      checkpoint_id: null,
      message_type: "text",
      role_type: "human",
      subtype: null,
      content: message,
      name: null,
      timestamp: new Date().toISOString(),
    };
    setBundle((prev) => ({ ...prev, events: [...prev.events, humanEvent] }));

    // These tools return Command(update=...) and never emit a tool_result on
    // the custom stream — so we detect completion via the LLM resuming after
    // ToolNode runs: the next AI text/reasoning event means state is committed.
    const STATE_MUTATING = new Set([
      "update_todos",
      "write_file",
      "edit_file",
      "create_file",
    ]);
    let pendingRefetch = false;

    async function refreshState() {
      const state = await fetch(`/api/threads/${activeId}/state`).then((r) => r.json());
      setBundle((prev) => ({
        ...prev,
        todos: state.todos,
        workspace: state.workspace,
      }));
    }

    setSending(true);
    try {
      await streamPost(
        `/api/threads/${activeId}/stream`,
        { message },
        (ev) => {
          setBundle((prev) => ({ ...prev, events: [...prev.events, ev] }));

          if (
            ev.role_type === "ai" &&
            ev.message_type === "tool_call" &&
            typeof ev.content === "object" &&
            STATE_MUTATING.has(ev.content?.name)
          ) {
            pendingRefetch = true;
            return;
          }

          if (
            pendingRefetch &&
            ev.role_type === "ai" &&
            ev.message_type !== "tool_call"
          ) {
            pendingRefetch = false;
            refreshState();
          }
        }
      );
      await refreshState();
    } catch (err) {
      console.error("Stream failed:", err);
    } finally {
      setSending(false);
    }
  }

  function handleSelectFile(file) {
    setBundle((prev) => ({
      ...prev,
      artifact: { title: file.path, content: file.content },
    }));
  }

  return (
    <div
      className="app"
      style={{ gridTemplateColumns: `240px 1fr ${chatWidth}px` }}
    >
      <Sidebar
        workspace={bundle.workspace}
        activePath={bundle.artifact?.title ?? null}
        onSelectFile={handleSelectFile}
      />
      <ArtifactPanel artifact={bundle.artifact} />
      <ChatPanel
        threads={threads}
        activeThreadId={activeId}
        onSelectThread={setActiveId}
        onNewThread={handleNewThread}
        onDeleteThread={handleDeleteThread}
        messages={messages}
        todos={bundle.todos}
        onSend={handleSend}
        sending={sending}
        chatWidth={chatWidth}
        onChatWidthChange={setChatWidth}
      />
    </div>
  );
}
