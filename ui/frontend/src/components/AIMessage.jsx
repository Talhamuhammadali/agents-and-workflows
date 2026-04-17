import { useState } from "react";
import { Sparkles, ChevronRight, Brain, Wrench } from "lucide-react";
import ToolCallItem from "./ToolCallItem";

// Find the matching tool result message for a given tool_call id
function findToolResult(toolCallId, allMessages, aiMessageIndex) {
  for (let i = aiMessageIndex + 1; i < allMessages.length; i++) {
    const msg = allMessages[i];
    if (msg.type === "tool" && msg.tool_call_id === toolCallId) return msg;
    if (msg.type === "human") break; // stop at next human turn
  }
  return null;
}

function ReasoningBlock({ block }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="reasoning-block">
      <button className="collapsible-header" onClick={() => setOpen(!open)}>
        <ChevronRight size={14} className={`chevron ${open ? "open" : ""}`} />
        <Brain size={13} className="reasoning-icon" />
        <span>Reasoning</span>
      </button>
      {open && (
        <div className="collapsible-body reasoning-content">
          {block.reasoning.split("\n").map((line, i) => (
            <p key={i}>{line || "\u00A0"}</p>
          ))}
        </div>
      )}
    </div>
  );
}

function TextBlock({ block }) {
  return (
    <div className="text-block">
      {block.text.split("\n").map((line, i) => (
        <p key={i}>{line || "\u00A0"}</p>
      ))}
    </div>
  );
}

function ToolCallsSection({ toolCalls, allMessages, messageIndex }) {
  const [open, setOpen] = useState(false);
  const count = toolCalls.length;

  return (
    <div className="tool-calls-section">
      <button className="collapsible-header" onClick={() => setOpen(!open)}>
        <ChevronRight size={14} className={`chevron ${open ? "open" : ""}`} />
        <Wrench size={13} className="tool-icon" />
        <span>
          {count} tool call{count > 1 ? "s" : ""}
        </span>
      </button>
      {open && (
        <div className="collapsible-body tool-calls-list">
          {toolCalls.map((tc) => (
            <ToolCallItem
              key={tc.id}
              toolCall={tc}
              toolResult={findToolResult(tc.id, allMessages, messageIndex)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function AIMessage({ message, allMessages, messageIndex }) {
  const blocks = message.content_blocks || [];
  const toolCalls = message.tool_calls || [];

  return (
    <div className="message ai-message">
      <div className="message-avatar">
        <Sparkles size={16} />
      </div>
      <div className="message-body">
        {message.name && <span className="agent-name">{message.name}</span>}

        {blocks.map((block, i) => {
          if (block.type === "reasoning") return <ReasoningBlock key={i} block={block} />;
          if (block.type === "text") return <TextBlock key={i} block={block} />;
          return null;
        })}

        {toolCalls.length > 0 && (
          <ToolCallsSection
            toolCalls={toolCalls}
            allMessages={allMessages}
            messageIndex={messageIndex}
          />
        )}
      </div>
    </div>
  );
}
