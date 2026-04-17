import { FileCode } from "lucide-react";

export default function ArtifactPanel({ artifact }) {
  if (!artifact) {
    return (
      <div className="artifact-panel empty">
        <p>No artifact selected</p>
      </div>
    );
  }

  return (
    <div className="artifact-panel">
      <div className="artifact-header">
        <FileCode size={16} />
        <span className="artifact-title">{artifact.title}</span>
        <span className="artifact-lang">{artifact.language}</span>
      </div>
      <pre className="artifact-content">
        <code>{artifact.content}</code>
      </pre>
    </div>
  );
}
