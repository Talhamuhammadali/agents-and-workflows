import { Send } from "lucide-react";
import HumanMessage from "./HumanMessage";
import AIMessage from "./AIMessage";
import TodoSection from "./TodoSection";

export default function ChatPanel({ messages, todos }) {
  // Only render human and ai messages (tool messages are shown inside AIMessage)
  const visibleMessages = messages.filter(
    (m) => m.type === "human" || m.type === "ai"
  );

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <h2>Chat</h2>
      </div>

      <div className="chat-messages">
        {visibleMessages.map((msg, i) => {
          // Find the original index in the full messages array (for tool result lookup)
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
            />
          );
        })}
      </div>

      {/* Todos sit just above the input */}
      <TodoSection todos={todos} />

      <div className="chat-input">
        <input type="text" placeholder="Type a message..." />
        <button className="send-btn">
          <Send size={16} />
        </button>
      </div>
    </div>
  );
}
