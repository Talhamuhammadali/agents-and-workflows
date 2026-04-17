import { useState } from "react";
import { Bot, ChevronRight, Brain, MessageSquare } from "lucide-react";
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

function ThinkingBlock({ block }) {
  const [open, setOpen] = useState(false);
  const content = block.thinking || block.reasoning || "";
  const label = block.type === "thinking" ? "Thinking" : "Reasoning";

  return (
    <div className="thinking-block">
      <button className="thinking-header" onClick={() => setOpen(!open)}>
        <ChevronRight
          size={14}
          className={`chevron ${open ? "open" : ""}`}
        />
        <Brain size={14} className="thinking-icon" />
        <span>{label}</span>
      </button>
      {open && (
        <div className="thinking-content">
          {content.split("\n").map((line, i) => (
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

export default function AIMessage({ message, allMessages, messageIndex }) {
  const blocks = message.content_blocks || [];
  const toolCalls = message.tool_calls || [];

  return (
    <div className="message ai-message">
      <div className="message-avatar">
        <Bot size={18} />
      </div>
      <div className="message-body">
        {message.name && (
          <span className="agent-name">{message.name}</span>
        )}

        {/* Content blocks: thinking/reasoning + text */}
        {blocks.map((block, i) => {
          if (block.type === "thinking" || block.type === "reasoning") {
            return <ThinkingBlock key={i} block={block} />;
          }
          if (block.type === "text") {
            return <TextBlock key={i} block={block} />;
          }
          return null;
        })}

        {/* Tool calls timeline */}
        {toolCalls.length > 0 && (
          <div className="tool-calls-section">
            <div className="tool-calls-label">
              <MessageSquare size={13} />
              <span>
                {toolCalls.length} tool call{toolCalls.length > 1 ? "s" : ""}
              </span>
            </div>
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
    </div>
  );
}
