"""Workspace snapshot for the UI.

Reuses `helpers.filesystem.FileSystem` — the same sandboxed reader the agent
tools use — so the sidebar shows the exact view the agent operates on.
"""

from pathlib import Path


async def list_workspace(workspace: str | Path | None) -> list[dict]:
    """Return every readable text file under `workspace`.

    Entry shape: `{path, name, content}` with `path` relative to the workspace
    root (POSIX-style). Returns `[]` when the workspace is missing or unset —
    callers typically source the path from the agent's persisted state.
    """
    if not workspace:
        return []
    root = Path(workspace)
    if not root.exists():
        return []

    # Local import keeps backend module import-safe if aiofiles isn't installed.
    from helpers.filesystem import FileSystem

    fs = FileSystem(workspace=str(root))
    paths = await fs.glob("**/*", limit=0)

    entries: list[dict] = []
    for rel in paths:
        try:
            content = await fs.read(rel, limit=10_000)
        except (UnicodeDecodeError, OSError, ValueError):
            continue
        entries.append({"path": rel, "name": Path(rel).name, "content": content})
    return entries
