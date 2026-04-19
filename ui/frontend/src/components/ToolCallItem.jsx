import { useEffect, useState } from "react";
import { ChevronRight, Wrench, CheckCircle2 } from "lucide-react";
import { renderToolCall } from "./toolRenderers";

export default function ToolCallItem({ toolCall, toolResult, isComplete, isLive }) {
  const [open, setOpen] = useState(!isComplete);

  // Stay expanded while running; collapse when the tool is done (either a
  // result arrived, the LLM resumed, or the turn ended).
  useEffect(() => {
    setOpen(!isComplete);
  }, [isComplete]);

  return (
    <div className={`tool-call-item ${isLive ? "live" : ""}`}>
      <button className="tool-call-header" onClick={() => setOpen(!open)}>
        <ChevronRight size={14} className={`chevron ${open ? "open" : ""}`} />
        <Wrench size={13} className={`tool-icon ${isLive ? "live-icon" : ""}`} />
        <span className={`tool-name ${isLive ? "live-label" : ""}`}>
          {toolCall.name}
        </span>
        {isComplete && !isLive && <CheckCircle2 size={13} className="tool-done-icon" />}
      </button>

      {open && (
        <div className="tool-call-details">
          {renderToolCall(toolCall, toolResult)}
        </div>
      )}
    </div>
  );
}
