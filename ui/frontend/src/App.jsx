import conversation from "./data/dummy";
import Sidebar from "./components/Sidebar";
import ArtifactPanel from "./components/ArtifactPanel";
import ChatPanel from "./components/ChatPanel";
import "./App.css";

export default function App() {
  return (
    <div className="app">
      <Sidebar workspace={conversation.workspace} />
      <ArtifactPanel artifact={conversation.artifact} />
      <ChatPanel
        messages={conversation.messages}
        todos={conversation.todos}
      />
    </div>
  );
}
