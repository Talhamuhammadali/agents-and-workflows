import { useEffect, useMemo, useState } from "react";
import { accumulate } from "./stream/accumulator";
import { streamPost } from "./stream/postStream";
import Sidebar from "./components/Sidebar";
import ArtifactPanel from "./components/ArtifactPanel";
import ChatPanel from "./components/ChatPanel";
import "./App.css";

const EMPTY_BUNDLE = { events: [], todos: [], workspace: [], artifact: null };

export default function App() {
  const [threads, setThreads] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [bundle, setBundle] = useState(EMPTY_BUNDLE);
  const [sending, setSending] = useState(false);

  const messages = useMemo(() => accumulate(bundle.events), [bundle.events]);

  // Load thread list on mount.
  useEffect(() => {
    fetch("/api/threads")
      .then((r) => r.json())
      .then((ts) => {
        setThreads(ts);
        if (ts[0]) setActiveId(ts[0].thread_id);
      })
      .catch((err) => console.error("Failed to load threads:", err));
  }, []);

  // Load messages + panel state in parallel whenever the active thread changes.
  useEffect(() => {
    if (!activeId) return;
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
    setSending(true);
    try {
      await streamPost(
        `/api/threads/${activeId}/stream`,
        { message },
        (ev) => setBundle((prev) => ({ ...prev, events: [...prev.events, ev] }))
      );
      // Re-fetch only panel state after the turn — messages were streamed in.
      const state = await fetch(`/api/threads/${activeId}/state`).then((r) => r.json());
      setBundle((prev) => ({ ...prev, ...state }));
    } catch (err) {
      console.error("Stream failed:", err);
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="app">
      <Sidebar workspace={bundle.workspace} />
      <ArtifactPanel artifact={bundle.artifact} />
      <ChatPanel
        threads={threads}
        activeThreadId={activeId}
        onSelectThread={setActiveId}
        messages={messages}
        todos={bundle.todos}
        onSend={handleSend}
        sending={sending}
      />
    </div>
  );
}
