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
    <div className="markdown-body">
      <Markdown>{block.text}</Markdown>
      {live && <span className="live-caret" />}
    </div>
  );
}

function ToolCallGroup({ items, allMessages, messageIndex, liveBlockIndex, hasBlocksAfter, messageIsLive }) {
  const results = items.map(({ block }) =>
    findToolResult(block.call.id, allMessages, messageIndex)
  );
  // A tool is "done" if its result arrived, OR the LLM resumed after this
  // group (next block exists — Command-returning tools like update_todos
  // never emit a result), OR the turn itself has ended.
  const allComplete =
    results.every(Boolean) || hasBlocksAfter || !messageIsLive;
  const count = items.length;

  const [open, setOpen] = useState(!allComplete);
  useEffect(() => {
    setOpen(!allComplete);
  }, [allComplete]);

  return (
    <div className="tool-call-group">
      <button className="collapsible-header" onClick={() => setOpen(!open)}>
        <ChevronRight size={14} className={`chevron ${open ? "open" : ""}`} />
        <Wrench size={13} className={`tool-icon ${!allComplete ? "live-icon" : ""}`} />
        <span className={!allComplete ? "live-label" : ""}>
          {allComplete
            ? `${count} tool call${count > 1 ? "s" : ""}`
            : `Running ${count} tool${count > 1 ? "s" : ""}…`}
        </span>
      </button>
      {open && (
        <div className="tool-call-group-body">
          {items.map(({ block, index }, i) => (
            <ToolCallItem
              key={block.call.id || index}
              toolCall={block.call}
              toolResult={results[i]}
              isComplete={!!results[i] || hasBlocksAfter || !messageIsLive}
              isLive={index === liveBlockIndex && messageIsLive}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// Collapse runs of adjacent tool_call blocks so they render as one visual
// group — preserves the "3 calls together" shape of agent turns.
function groupBlocks(blocks) {
  const groups = [];
  for (let i = 0; i < blocks.length; i++) {
    const block = blocks[i];
    if (block.type !== "tool_call") {
      groups.push({ kind: "single", block, index: i });
      continue;
    }
    const run = [{ block, index: i }];
    while (i + 1 < blocks.length && blocks[i + 1].type === "tool_call") {
      i += 1;
      run.push({ block: blocks[i], index: i });
    }
    groups.push({ kind: "tool_group", items: run });
  }
  return groups;
}

export default function AIMessage({ message, allMessages, messageIndex, isLive }) {
  const blocks = message.content_blocks || [];
  const liveKey = isLive ? message.liveKey : null;
  const liveBlockIndex = liveKey?.kind === "block" ? liveKey.index : -1;

  const groups = groupBlocks(blocks);

  return (
    <div className="message">
      <div className="message-avatar">
        <Sparkles size={16} />
      </div>
      <div className="message-body">
        {message.name && <span className="agent-name">{message.name}</span>}

        {groups.map((group, gi) => {
          if (group.kind === "single") {
            const { block, index } = group;
            const live = index === liveBlockIndex;
            if (block.type === "reasoning") {
              return <ReasoningBlock key={gi} block={block} live={live} />;
            }
            if (block.type === "text") {
              return <TextBlock key={gi} block={block} live={live} />;
            }
            return null;
          }
          return (
            <ToolCallGroup
              key={gi}
              items={group.items}
              allMessages={allMessages}
              messageIndex={messageIndex}
              liveBlockIndex={liveBlockIndex}
              hasBlocksAfter={gi < groups.length - 1}
              messageIsLive={isLive}
            />
          );
        })}
      </div>
    </div>
  );
}
