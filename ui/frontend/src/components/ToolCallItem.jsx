import { useState } from "react";
import { ChevronRight, Wrench, CheckCircle2 } from "lucide-react";
import { renderToolCall } from "./toolRenderers";

export default function ToolCallItem({ toolCall, toolResult }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="tool-call-item">
      <button className="tool-call-header" onClick={() => setOpen(!open)}>
        <ChevronRight size={14} className={`chevron ${open ? "open" : ""}`} />
        <Wrench size={13} className="tool-icon" />
        <span className="tool-name">{toolCall.name}</span>
        {toolResult && <CheckCircle2 size={13} className="tool-done-icon" />}
      </button>

      {open && (
        <div className="tool-call-details">
          {renderToolCall(toolCall, toolResult)}
        </div>
      )}
    </div>
  );
}
