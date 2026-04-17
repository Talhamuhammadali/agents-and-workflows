import { FileText, Folder, Plus } from "lucide-react";

export default function Sidebar({ workspace }) {
  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <h2>Workspace</h2>
        <button className="icon-btn" title="New file">
          <Plus size={16} />
        </button>
      </div>

      <div className="file-tree">
        {workspace.map((item) => (
          <div key={item.name} className="file-item">
            {item.type === "folder" ? (
              <Folder size={14} className="file-icon folder-icon" />
            ) : (
              <FileText size={14} className="file-icon" />
            )}
            <span>{item.name}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
