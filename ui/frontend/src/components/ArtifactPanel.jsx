import { FileCode, FileText } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import Editor from "@monaco-editor/react";

function extOf(path) {
  const name = (path || "").split("/").pop() || "";
  const i = name.lastIndexOf(".");
  return i === -1 ? "" : name.slice(i + 1).toLowerCase();
}

export default function ArtifactPanel({ artifact }) {
  if (!artifact) {
    return (
      <div className="artifact-panel empty">
        <p>No artifact selected</p>
      </div>
    );
  }

  const ext = extOf(artifact.title);
  const isMarkdown = ext === "md" || ext === "markdown";
  const Icon = isMarkdown ? FileText : FileCode;

  return (
    <div className="artifact-panel">
      <div className="artifact-header">
        <Icon size={16} />
        <span className="artifact-title">{artifact.title}</span>
      </div>
      {isMarkdown ? (
        <div className="artifact-body markdown-body">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {artifact.content || ""}
          </ReactMarkdown>
        </div>
      ) : (
        <div className="artifact-body">
          <Editor
            height="100%"
            path={artifact.title}
            value={artifact.content || ""}
            theme="vs-dark"
            options={{
              readOnly: true,
              minimap: { enabled: false },
              wordWrap: "off",
              scrollBeyondLastLine: false,
              fontSize: 13,
              fontFamily: "var(--font-mono)",
              lineNumbers: "on",
            }}
          />
        </div>
      )}
    </div>
  );
}
