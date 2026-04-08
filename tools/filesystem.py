from pathlib import Path

import aiofiles


class FileSystem:
    """Sandboxed filesystem operations scoped to a workspace directory."""

    def __init__(self, workspace: str, allow_system_install: bool = False) -> None:
        """Initialize filesystem with a workspace root directory."""
        workspace_path = Path(workspace).resolve()
        if not workspace_path.is_dir():
            raise ValueError(f"Workspace directory does not exist: {workspace_path}")
        self.workspace = workspace_path
        self.allow_system_install = allow_system_install

    def _safe_path(self, path: str) -> Path:
        """Resolve path relative to workspace and block escapes."""
        resolved = (self.workspace / path).resolve()
        if not resolved.is_relative_to(self.workspace):
            raise PermissionError(f"Path escapes workspace: {path}")
        return resolved

    async def read(self, path: str, offset: int = 0, limit: int = 2000) -> str:
        """Read file contents with optional line offset and limit."""
        file_path = self._safe_path(path)
        if not file_path.is_file():
            raise FileNotFoundError(f"File not found: {path}")

        async with aiofiles.open(file_path) as f:
            lines = await f.readlines()

        selected = lines[offset : offset + limit]
        return "".join(selected)

    async def write(self, path: str, content: str) -> str:
        """Write content to a file. Parent directory must exist."""
        file_path = self._safe_path(path)
        if not file_path.parent.is_dir():
            raise FileNotFoundError(f"Parent directory does not exist: {file_path.parent}")

        async with aiofiles.open(file_path, "w") as f:
            await f.write(content)

        return str(file_path)

    async def edit(
        self,
        path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
    ) -> str:
        """Find and replace text in a file."""
        file_path = self._safe_path(path)
        if not file_path.is_file():
            raise FileNotFoundError(f"File not found: {path}")

        async with aiofiles.open(file_path) as f:
            content = await f.read()

        if old_string not in content:
            raise ValueError(f"String not found in {path}")

        if not replace_all and content.count(old_string) > 1:
            raise ValueError(f"Multiple occurrences found in {path}. Use replace_all=True or provide more context.")

        updated = content.replace(old_string, new_string) if replace_all else content.replace(old_string, new_string, 1)

        async with aiofiles.open(file_path, "w") as f:
            await f.write(updated)

        return str(file_path)
