import asyncio
import os
import re
import shlex
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import aiofiles


class FileSystem:
    """Sandboxed filesystem operations scoped to a workspace directory."""

    _BLOCKED_COMMANDS = frozenset({"apt", "apt-get", "yum", "dnf", "pacman", "sudo"})

    def __init__(self, workspace: str, allow_system_install: bool = False) -> None:
        """Initialize filesystem with a workspace oot directory."""
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

    async def glob(self, pattern: str, path: str = ".", limit: int = 200) -> list[str]:
        """Find files matching a glob pattern, sorted by modification time."""
        search_dir = self._safe_path(path)
        if not search_dir.is_dir():
            raise FileNotFoundError(f"Directory not found: {path}")

        matches = []
        for match in search_dir.glob(pattern):
            resolved = match.resolve()
            if not resolved.is_relative_to(self.workspace):
                continue
            if resolved.is_file():
                matches.append(resolved)

        matches.sort(key=lambda p: os.path.getmtime(p), reverse=True)

        limited = matches[:limit] if limit > 0 else matches
        return [str(m.relative_to(self.workspace)) for m in limited]

    async def grep(
        self,
        pattern: str,
        path: str = ".",
        *,
        glob: str | None = None,
        file_type: str | None = None,
        output_mode: str = "files_with_matches",
        after: int = 0,
        before: int = 0,
        context: int = 0,
        case_insensitive: bool = False,
        show_line_numbers: bool = True,
        multiline: bool = False,
        head_limit: int = 250,
        offset: int = 0,
    ) -> list[str] | list[dict]:
        """Search file contents using regex patterns."""
        if context > 0:
            before = context
            after = context

        flags = 0
        if case_insensitive:
            flags |= re.IGNORECASE
        if multiline:
            flags |= re.MULTILINE | re.DOTALL

        regex = re.compile(pattern, flags)

        # Determine glob pattern: file_type takes priority over glob.
        file_glob = f"**/*.{file_type}" if file_type else (glob or "**/*")
        file_paths = await self.glob(file_glob, path=path, limit=0)

        results: list[Any] = []
        skipped = 0

        for rel_path in file_paths:
            file_path = self._safe_path(rel_path)

            try:
                async with aiofiles.open(file_path) as f:
                    content = await f.read()
            except (UnicodeDecodeError, PermissionError):
                continue

            if multiline:
                if not regex.search(content):
                    continue
                if output_mode == "files_with_matches":
                    if skipped < offset:
                        skipped += 1
                        continue
                    results.append(rel_path)
                elif output_mode == "count":
                    if skipped < offset:
                        skipped += 1
                        continue
                    results.append({"file": rel_path, "count": len(regex.findall(content))})
                elif output_mode == "content":
                    for m in regex.finditer(content):
                        if skipped < offset:
                            skipped += 1
                            continue
                        results.append({"file": rel_path, "match": m.group()})
                        if len(results) >= head_limit:
                            return results
                continue

            lines = content.splitlines()

            if output_mode == "files_with_matches":
                if any(regex.search(line) for line in lines):
                    if skipped < offset:
                        skipped += 1
                        continue
                    results.append(rel_path)

            elif output_mode == "count":
                count = sum(1 for line in lines if regex.search(line))
                if count > 0:
                    if skipped < offset:
                        skipped += 1
                        continue
                    results.append({"file": rel_path, "count": count})

            elif output_mode == "content":
                for i, line in enumerate(lines):
                    if not regex.search(line):
                        continue
                    if skipped < offset:
                        skipped += 1
                        continue

                    start = max(0, i - before)
                    end = min(len(lines), i + after + 1)
                    ctx_lines = []
                    for j in range(start, end):
                        prefix = f"{j + 1}\t" if show_line_numbers else ""
                        ctx_lines.append(f"{prefix}{lines[j]}")

                    results.append({"file": rel_path, "lines": "\n".join(ctx_lines)})

                    if len(results) >= head_limit:
                        return results

            if len(results) >= head_limit:
                break

        return results

    def _check_command(self, command: str) -> None:
        """Validate command against sandbox rules."""
        tokens = shlex.split(command)
        if not tokens:
            raise ValueError("Empty command")
        if tokens[0] in self._BLOCKED_COMMANDS and not self.allow_system_install:
            raise PermissionError(
                f"System install commands are blocked: {tokens[0]}. Set allow_system_install=True to allow."
            )

    async def bash(
        self,
        command: str,
        timeout: int = 120,
        run_in_background: bool = False,
    ) -> AsyncGenerator[str, None] | dict:
        """Execute a shell command sandboxed to the workspace."""
        self._check_command(command)

        if run_in_background:
            proc = await asyncio.create_subprocess_shell(
                command,
                cwd=self.workspace,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            except TimeoutError:
                proc.kill()
                await proc.communicate()
                return {
                    "exit_code": -1,
                    "stdout": "",
                    "stderr": "Command timed out",
                }
            return {
                "exit_code": proc.returncode,
                "stdout": stdout.decode(errors="replace"),
                "stderr": stderr.decode(errors="replace"),
            }

        return self._stream_command(command, timeout)

    async def _stream_command(self, command: str, timeout: int) -> AsyncGenerator[str, None]:
        """Stream command output line by line."""
        proc = await asyncio.create_subprocess_shell(
            command,
            cwd=self.workspace,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        deadline = asyncio.get_event_loop().time() + timeout

        if proc.stdout is None:
            await proc.wait()
            return

        async for line in proc.stdout:
            if asyncio.get_event_loop().time() > deadline:
                proc.kill()
                yield "[timed out]"
                break
            yield line.decode(errors="replace")

        await proc.wait()
