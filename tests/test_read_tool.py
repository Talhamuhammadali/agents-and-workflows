"""Tests for read_file tool — unchanged detection logic."""

from dataclasses import dataclass
from pathlib import Path

import pytest
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import ToolRuntime

from agentic_patterns.shared.helper import content_hash
from agentic_patterns.shared.workspace_tools import read_file
from helpers.filesystem import FileSystem

SANDBOX = Path(__file__).parent / "workspaces" / "sandbox"


# --- Helpers ---


@dataclass
class FakeContext:
    workspace: Path


def make_runtime(messages: list | None = None) -> ToolRuntime:
    """Build a ToolRuntime seeded with sandbox workspace and message history."""
    return ToolRuntime(
        state={"messages": messages or []},
        context=FakeContext(workspace=SANDBOX),
        config={},
        stream_writer=lambda x: None,
        tool_call_id="test-call-123",
        store=None,
    )


def file_tool_message(tool_name: str, path: str, file_content: str) -> ToolMessage:
    """Create a ToolMessage with response_metadata matching what read/write tools produce."""
    return ToolMessage(
        content="ok",
        tool_call_id="tc-1",
        response_metadata={
            "path": path,
            "tool_name": tool_name,
            "content_hash": content_hash(file_content),
        },
    )


def extract_content(command) -> str:
    """Pull text content from a Command's first ToolMessage."""
    return command.update["messages"][0].content


# --- Tests ---


class TestReadUnchangedDetection:

    @pytest.mark.asyncio
    async def test_first_read_no_history(self):
        rt = make_runtime(messages=[])
        result = await read_file.coroutine(tool_runtime=rt, path="src/utils.py")
        content = extract_content(result)
        assert "1\t" in content
        assert "format_name" in content

    @pytest.mark.asyncio
    async def test_read_after_write_same_path(self):
        fs = FileSystem(str(SANDBOX))
        original = await fs.read("src/utils.py")
        messages = [file_tool_message("write_file", "src/utils.py", original)]
        rt = make_runtime(messages=messages)
        result = await read_file.coroutine(tool_runtime=rt, path="src/utils.py")
        content = extract_content(result)
        assert "unchanged" in content.lower()

    @pytest.mark.asyncio
    async def test_read_after_read_same_path(self):
        fs = FileSystem(str(SANDBOX))
        original = await fs.read("src/utils.py")
        messages = [file_tool_message("read_file", "src/utils.py", original)]
        rt = make_runtime(messages=messages)
        result = await read_file.coroutine(tool_runtime=rt, path="src/utils.py")
        content = extract_content(result)
        assert "unchanged" in content.lower()

    @pytest.mark.asyncio
    async def test_different_path_not_affected(self):
        fs = FileSystem(str(SANDBOX))
        config_content = await fs.read("config.json")
        messages = [file_tool_message("read_file", "config.json", config_content)]
        rt = make_runtime(messages=messages)
        result = await read_file.coroutine(tool_runtime=rt, path="src/utils.py")
        content = extract_content(result)
        assert "format_name" in content

    @pytest.mark.asyncio
    async def test_read_after_write_file_changed(self):
        """History has write_file but file was modified externally since → should return new content."""
        fs = FileSystem(str(SANDBOX))
        original = await fs.read("src/utils.py")
        try:
            messages = [file_tool_message("write_file", "src/utils.py", original)]
            await fs.edit("src/utils.py", "format_name", "format_full_name")
            rt = make_runtime(messages=messages)
            result = await read_file.coroutine(tool_runtime=rt, path="src/utils.py")
            content = extract_content(result)
            assert "format_full_name" in content
        finally:
            await fs.write("src/utils.py", original)

    @pytest.mark.asyncio
    async def test_read_after_read_file_changed(self):
        """History has read_file but file changed externally since → should return new content."""
        fs = FileSystem(str(SANDBOX))
        original = await fs.read("src/utils.py")
        try:
            messages = [file_tool_message("read_file", "src/utils.py", original)]
            await fs.edit("src/utils.py", "reverse_string", "flip_string")
            rt = make_runtime(messages=messages)
            result = await read_file.coroutine(tool_runtime=rt, path="src/utils.py")
            content = extract_content(result)
            assert "flip_string" in content
        finally:
            await fs.write("src/utils.py", original)


class TestReadForceFlag:

    @pytest.mark.asyncio
    async def test_force_bypasses_unchanged(self):
        fs = FileSystem(str(SANDBOX))
        original = await fs.read("src/utils.py")
        messages = [file_tool_message("read_file", "src/utils.py", original)]
        rt = make_runtime(messages=messages)
        result = await read_file.coroutine(tool_runtime=rt, path="src/utils.py", force=True)
        content = extract_content(result)
        assert "format_name" in content


class TestReadErrors:

    @pytest.mark.asyncio
    async def test_file_not_found(self):
        rt = make_runtime()
        result = await read_file.coroutine(tool_runtime=rt, path="nope.txt")
        content = extract_content(result)
        assert "not found" in content.lower()

    @pytest.mark.asyncio
    async def test_path_escape_blocked(self):
        rt = make_runtime()
        result = await read_file.coroutine(tool_runtime=rt, path="../../etc/passwd")
        content = extract_content(result)
        assert "permission denied" in content.lower()


class TestReadTokenLimit:

    @pytest.mark.asyncio
    async def test_file_too_large(self):
        """File exceeding 20k tokens → error with grep_search guidance."""
        fs = FileSystem(str(SANDBOX))
        large_content = "x" * 100_000  # ~25k tokens
        try:
            await fs.write("large_file.txt", large_content)
            rt = make_runtime()
            result = await read_file.coroutine(tool_runtime=rt, path="large_file.txt")
            content = extract_content(result)
            assert "too large" in content.lower()
            assert "grep_search" in content
        finally:
            (SANDBOX / "large_file.txt").unlink(missing_ok=True)


class TestReadOffsetLimit:

    @pytest.mark.asyncio
    async def test_offset(self):
        rt = make_runtime()
        result = await read_file.coroutine(tool_runtime=rt, path="src/utils.py", offset=3)
        content = extract_content(result)
        assert "format_name" in content
        assert '"""Utility functions' not in content

    @pytest.mark.asyncio
    async def test_limit(self):
        rt = make_runtime()
        result = await read_file.coroutine(tool_runtime=rt, path="src/utils.py", limit=2)
        content = extract_content(result)
        assert '"""Utility functions' in content
        assert "format_name" not in content
