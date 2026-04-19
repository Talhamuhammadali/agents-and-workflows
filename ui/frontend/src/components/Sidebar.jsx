import { useState } from "react";
import { ChevronRight, FileText, Folder, FolderOpen } from "lucide-react";

// Turn a flat `[{path, name, content}]` list into a nested tree of
// folder/file nodes. Paths are split on "/" — POSIX-style from the backend.
function buildTree(files) {
  const root = { type: "folder", name: "", path: "", children: new Map() };
  for (const file of files) {
    const parts = file.path.split("/");
    let node = root;
    for (let i = 0; i < parts.length - 1; i++) {
      const segment = parts[i];
      const folderPath = parts.slice(0, i + 1).join("/");
      if (!node.children.has(segment)) {
        node.children.set(segment, {
          type: "folder",
          name: segment,
          path: folderPath,
          children: new Map(),
        });
      }
      node = node.children.get(segment);
    }
    const leaf = parts[parts.length - 1];
    node.children.set(leaf, {
      type: "file",
      name: leaf,
      path: file.path,
      content: file.content,
    });
  }
  return finalize(root);
}

// Convert the Map-based intermediate tree into arrays, folders first.
function finalize(node) {
  if (node.type === "file") return node;
  const entries = [...node.children.values()].map(finalize);
  entries.sort((a, b) => {
    if (a.type !== b.type) return a.type === "folder" ? -1 : 1;
    return a.name.localeCompare(b.name);
  });
  return { ...node, children: entries };
}

function FolderNode({ node, depth, activePath, onSelectFile }) {
  const [open, setOpen] = useState(depth === 0);
  const Icon = open ? FolderOpen : Folder;
  return (
    <>
      <button
        className="file-item"
        style={{ paddingLeft: 10 + depth * 14 }}
        onClick={() => setOpen(!open)}
      >
        <ChevronRight size={12} className={`chevron ${open ? "open" : ""}`} />
        <Icon size={14} className="file-icon folder-icon" />
        <span className="file-item-name">{node.name}</span>
      </button>
      {open &&
        node.children.map((child) =>
          child.type === "folder" ? (
            <FolderNode
              key={child.path}
              node={child}
              depth={depth + 1}
              activePath={activePath}
              onSelectFile={onSelectFile}
            />
          ) : (
            <FileNode
              key={child.path}
              node={child}
              depth={depth + 1}
              activePath={activePath}
              onSelectFile={onSelectFile}
            />
          )
        )}
    </>
  );
}

function FileNode({ node, depth, activePath, onSelectFile }) {
  return (
    <button
      className={`file-item ${node.path === activePath ? "active" : ""}`}
      style={{ paddingLeft: 10 + depth * 14 + 14 }}
      onClick={() => onSelectFile?.(node)}
      title={node.path}
    >
      <FileText size={14} className="file-icon" />
      <span className="file-item-name">{node.name}</span>
    </button>
  );
}

export default function Sidebar({ workspace, activePath, onSelectFile }) {
  const tree = buildTree(workspace);
  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <h2>Workspace</h2>
      </div>

      <div className="file-tree">
        {workspace.length === 0 && (
          <div className="file-tree-empty">No files yet</div>
        )}
        {tree.children.map((node) =>
          node.type === "folder" ? (
            <FolderNode
              key={node.path}
              node={node}
              depth={0}
              activePath={activePath}
              onSelectFile={onSelectFile}
            />
          ) : (
            <FileNode
              key={node.path}
              node={node}
              depth={0}
              activePath={activePath}
              onSelectFile={onSelectFile}
            />
          )
        )}
      </div>
    </div>
  );
}
