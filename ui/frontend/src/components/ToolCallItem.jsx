import { useEffect, useState } from "react";
import { ChevronRight, Wrench, CheckCircle2 } from "lucide-react";
import { renderToolCall } from "./toolRenderers";

export default function ToolCallItem({ toolCall, toolResult, isLive }) {
  const [open, setOpen] = useState(isLive);

  // Track the active tool only: open on live, collapse once it's no longer
  // the active one. User can still click to re-expand finished tools.
  useEffect(() => {
    setOpen(isLive);
  }, [isLive]);

  return (
    <div className={`tool-call-item ${isLive ? "live" : ""}`}>
      <button className="tool-call-header" onClick={() => setOpen(!open)}>
        <ChevronRight size={14} className={`chevron ${open ? "open" : ""}`} />
        <Wrench size={13} className={`tool-icon ${isLive ? "live-icon" : ""}`} />
        <span className={`tool-name ${isLive ? "live-label" : ""}`}>
          {toolCall.name}
        </span>
        {toolResult && !isLive && <CheckCircle2 size={13} className="tool-done-icon" />}
      </button>

      {open && (
        <div className="tool-call-details">
          {renderToolCall(toolCall, toolResult)}
        </div>
      )}
    </div>
  );
}
