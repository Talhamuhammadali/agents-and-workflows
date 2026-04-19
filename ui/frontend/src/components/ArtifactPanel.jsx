import { FileCode, FileText } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";

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
          <SyntaxHighlighter
            // Prism resolves most extensions via its alias table (py, ts,
            // sh, yml, rs, ...). Unknown ones fall back to plain text.
            language={ext || "text"}
            style={oneDark}
            showLineNumbers
            customStyle={{
              margin: 0,
              padding: 0,
              background: "transparent",
              fontSize: "var(--text-base)",
              fontFamily: "var(--font-mono)",
            }}
            codeTagProps={{ style: { fontFamily: "var(--font-mono)" } }}
          >
            {artifact.content || ""}
          </SyntaxHighlighter>
        </div>
      )}
    </div>
  );
}
