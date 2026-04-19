import { useEffect, useState } from "react";
import { Sparkles, ChevronRight, Brain, Wrench } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import ToolCallItem from "./ToolCallItem";

function Markdown({ children }) {
  return (
    <ReactMarkdown remarkPlugins={[remarkGfm]}>
      {children || ""}
    </ReactMarkdown>
  );
}

// Find the matching tool result message for a given tool_call id
function findToolResult(toolCallId, allMessages, aiMessageIndex) {
  for (let i = aiMessageIndex + 1; i < allMessages.length; i++) {
    const msg = allMessages[i];
    if (msg.type === "tool" && msg.tool_call_id === toolCallId) return msg;
    if (msg.type === "human") break; // stop at next human turn
  }
  return null;
}

function ReasoningBlock({ block, live }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="reasoning-block">
      <button className="collapsible-header" onClick={() => setOpen(!open)}>
        <ChevronRight size={14} className={`chevron ${open ? "open" : ""}`} />
        <Brain size={13} className={`reasoning-icon ${live ? "live-icon" : ""}`} />
        <span className={live ? "live-label" : ""}>
          {live ? "Reasoning…" : "Reasoning"}
        </span>
      </button>
      {open && (
        <div className="collapsible-body reasoning-content markdown-body">
          <Markdown>{block.reasoning}</Markdown>
        </div>
      )}
    </div>
  );
}

function TextBlock({ block, live }) {
  return (
    <div className={`text-block markdown-body ${live ? "live" : ""}`}>
      <Markdown>{block.text}</Markdown>
      {live && <span className="live-caret" />}
    </div>
  );
}

function ToolCallsSection({ toolCalls, allMessages, messageIndex, sectionLive, liveCallId }) {
  const [open, setOpen] = useState(sectionLive);
  const count = toolCalls.length;

  useEffect(() => {
    if (sectionLive) setOpen(true);
  }, [sectionLive]);

  return (
    <div className="tool-calls-section">
      <button className="collapsible-header" onClick={() => setOpen(!open)}>
        <ChevronRight size={14} className={`chevron ${open ? "open" : ""}`} />
        <Wrench size={13} className={`tool-icon ${sectionLive ? "live-icon" : ""}`} />
        <span className={sectionLive ? "live-label" : ""}>
          {sectionLive ? "Running tools…" : `${count} tool call${count > 1 ? "s" : ""}`}
        </span>
      </button>
      {open && (
        <div className="collapsible-body tool-calls-list">
          {toolCalls.map((tc) => (
            <ToolCallItem
              key={tc.id}
              toolCall={tc}
              toolResult={findToolResult(tc.id, allMessages, messageIndex)}
              isLive={tc.id === liveCallId}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function AIMessage({ message, allMessages, messageIndex, isLive }) {
  const blocks = message.content_blocks || [];
  const toolCalls = message.tool_calls || [];
  const liveKey = isLive ? message.liveKey : null;

  const liveBlockIndex = liveKey?.kind === "block" ? liveKey.index : -1;
  const sectionLive = liveKey?.kind === "tool";
  const liveCallId = liveKey?.kind === "tool" ? liveKey.callId : null;

  return (
    <div className="message ai-message">
      <div className="message-avatar">
        <Sparkles size={16} />
      </div>
      <div className="message-body">
        {message.name && <span className="agent-name">{message.name}</span>}

        {blocks.map((block, i) => {
          const live = i === liveBlockIndex;
          if (block.type === "reasoning") return <ReasoningBlock key={i} block={block} live={live} />;
          if (block.type === "text") return <TextBlock key={i} block={block} live={live} />;
          return null;
        })}

        {toolCalls.length > 0 && (
          <ToolCallsSection
            toolCalls={toolCalls}
            allMessages={allMessages}
            messageIndex={messageIndex}
            sectionLive={sectionLive}
            liveCallId={liveCallId}
          />
        )}
      </div>
    </div>
  );
}
