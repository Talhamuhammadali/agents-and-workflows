import { useState } from "react";
import { ChevronRight, Wrench, CheckCircle2 } from "lucide-react";

export default function ToolCallItem({ toolCall, toolResult }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="tool-call-item">
      <button className="tool-call-header" onClick={() => setOpen(!open)}>
        <ChevronRight
          size={14}
          className={`chevron ${open ? "open" : ""}`}
        />
        <Wrench size={13} className="tool-icon" />
        <span className="tool-name">{toolCall.name}</span>
        {toolResult && <CheckCircle2 size={13} className="tool-done-icon" />}
      </button>

      {open && (
        <div className="tool-call-details">
          <div className="tool-detail-section">
            <span className="tool-detail-label">Input</span>
            <pre>{JSON.stringify(toolCall.args, null, 2)}</pre>
          </div>
          {toolResult && (
            <div className="tool-detail-section">
              <span className="tool-detail-label">Output</span>
              <pre>{toolResult.content}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
