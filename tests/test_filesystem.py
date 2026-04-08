"""Tests for FileSystem Shell and search utilities."""

from pathlib import Path

import pytest

from tools.filesystem import FileSystem


class TestGlob:
    """Tests for glob method."""

    @pytest.mark.asyncio
    async def test_glob_txt_files(self, fs: FileSystem):
        """Finds .txt files in workspace."""
        results = await fs.glob("*.txt")
        assert "hello.txt" in results

    @pytest.mark.asyncio
    async def test_glob_recursive(self, fs: FileSystem):
        """Finds files recursively with ** pattern."""
        results = await fs.glob("**/*.txt")
        assert "hello.txt" in results
        assert "subdir/nested.txt" in results

    @pytest.mark.asyncio
    async def test_glob_scoped_to_subdir(self, fs: FileSystem):
        """Scopes search to a subdirectory."""
        results = await fs.glob("*.txt", path="subdir")
        assert "subdir/nested.txt" in results
        assert "hello.txt" not in results

    @pytest.mark.asyncio
    async def test_glob_no_matches(self, fs: FileSystem):
        """Returns empty list when no files match."""
        results = await fs.glob("*.xyz")
        assert results == []

    @pytest.mark.asyncio
    async def test_glob_limit(self, fs: FileSystem, workspace: Path):
        """Respects the result limit."""
        for i in range(5):
            (workspace / f"file{i}.md").write_text(f"content {i}")
        results = await fs.glob("*.md", limit=3)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_glob_sorted_by_mtime(self, fs: FileSystem, workspace: Path):
        """Returns results sorted by modification time, newest first."""
        import time

        (workspace / "old.md").write_text("old")
        time.sleep(0.05)
        (workspace / "new.md").write_text("new")
        results = await fs.glob("*.md")
        assert results[0] == "new.md"
        assert results[1] == "old.md"

    @pytest.mark.asyncio
    async def test_glob_filters_symlinks_outside(self, fs: FileSystem, workspace: Path):
        """Filters out symlinks pointing outside workspace."""
        outside = workspace.parent / "outside_file.txt"
        outside.write_text("external")
        (workspace / "link.txt").symlink_to(outside)
        results = await fs.glob("*.txt")
        assert "link.txt" not in results

    @pytest.mark.asyncio
    async def test_glob_nonexistent_dir(self, fs: FileSystem):
        """Raises FileNotFoundError for missing directory."""
        with pytest.raises(FileNotFoundError, match="Directory not found"):
            await fs.glob("*.txt", path="nope")

    @pytest.mark.asyncio
    async def test_glob_traversal_blocked(self, fs: FileSystem):
        """Blocks glob in directories outside workspace."""
        with pytest.raises(PermissionError):
            await fs.glob("*.txt", path="../../etc")


class TestGrep:
    """Tests for grep method."""

    @pytest.mark.asyncio
    async def test_files_with_matches(self, fs: FileSystem):
        """Returns file paths containing the pattern."""
        results = await fs.grep("def ")
        assert "app.py" in results
        assert "utils.py" in results
        assert "hello.txt" not in results

    @pytest.mark.asyncio
    async def test_content_mode(self, fs: FileSystem):
        """Returns matching lines with line numbers."""
        results = await fs.grep("print", output_mode="content")
        assert len(results) > 0
        assert "file" in results[0]
        assert "lines" in results[0]
        assert "print" in results[0]["lines"]

    @pytest.mark.asyncio
    async def test_content_line_numbers(self, fs: FileSystem):
        """Shows line numbers in content mode by default."""
        results = await fs.grep("import os", output_mode="content")
        assert len(results) == 1
        assert results[0]["lines"].startswith("1\t")

    @pytest.mark.asyncio
    async def test_content_no_line_numbers(self, fs: FileSystem):
        """Hides line numbers when show_line_numbers is False."""
        results = await fs.grep("import os", output_mode="content", show_line_numbers=False)
        assert not results[0]["lines"].startswith("1\t")

    @pytest.mark.asyncio
    async def test_count_mode(self, fs: FileSystem):
        """Returns match counts per file."""
        results = await fs.grep("def ", output_mode="count")
        counts = {r["file"]: r["count"] for r in results}
        assert counts["utils.py"] == 2
        assert counts["app.py"] == 1

    @pytest.mark.asyncio
    async def test_case_insensitive(self, fs: FileSystem, workspace: Path):
        """Matches case-insensitively when flag is set."""
        (workspace / "caps.txt").write_text("Hello\nhello\nHELLO\n")
        results = await fs.grep("hello", output_mode="count", case_insensitive=True)
        counts = {r["file"]: r["count"] for r in results}
        assert counts["caps.txt"] == 3

    @pytest.mark.asyncio
    async def test_context_lines(self, fs: FileSystem):
        """Includes context lines around matches."""
        results = await fs.grep("return 0", output_mode="content", context=1)
        lines = results[0]["lines"]
        assert "print" in lines
        assert "return 0" in lines

    @pytest.mark.asyncio
    async def test_after_lines(self, fs: FileSystem):
        """Includes lines after match."""
        results = await fs.grep("import os", output_mode="content", after=1)
        assert "\n" in results[0]["lines"]

    @pytest.mark.asyncio
    async def test_before_lines(self, fs: FileSystem):
        """Includes lines before match."""
        results = await fs.grep("return 0", output_mode="content", before=1)
        lines = results[0]["lines"]
        assert "print" in lines

    @pytest.mark.asyncio
    async def test_file_type_filter(self, fs: FileSystem):
        """Filters by file type."""
        results = await fs.grep("def ", file_type="py")
        assert all(r.endswith(".py") for r in results)

    @pytest.mark.asyncio
    async def test_glob_filter(self, fs: FileSystem):
        """Filters by glob pattern."""
        results = await fs.grep("def ", glob="**/*.py")
        assert all(r.endswith(".py") for r in results)

    @pytest.mark.asyncio
    async def test_scoped_to_subdir(self, fs: FileSystem):
        """Scopes search to a subdirectory."""
        results = await fs.grep("def ", path="subdir")
        assert all(r.startswith("subdir/") for r in results)

    @pytest.mark.asyncio
    async def test_head_limit(self, fs: FileSystem):
        """Respects head_limit on results."""
        results = await fs.grep("def ", output_mode="content", head_limit=1)
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_offset(self, fs: FileSystem):
        """Skips first N results."""
        all_results = await fs.grep("def ")
        offset_results = await fs.grep("def ", offset=1)
        assert len(offset_results) == len(all_results) - 1

    @pytest.mark.asyncio
    async def test_multiline(self, fs: FileSystem):
        """Matches patterns across lines."""
        results = await fs.grep(r"def main.*return 0", multiline=True)
        assert "app.py" in results

    @pytest.mark.asyncio
    async def test_no_matches(self, fs: FileSystem):
        """Returns empty list when nothing matches."""
        results = await fs.grep("zzz_nonexistent_pattern")
        assert results == []

    @pytest.mark.asyncio
    async def test_traversal_blocked(self, fs: FileSystem):
        """Blocks searching outside workspace."""
        with pytest.raises(PermissionError):
            await fs.grep("root", path="../../etc")


class TestBash:
    """Tests for bash method."""

    @pytest.mark.asyncio
    async def test_stream_output(self, fs: FileSystem):
        """Streams command output line by line."""
        lines = []
        stream = await fs.bash("echo 'hello\nworld'")
        async for line in stream:
            lines.append(line.strip())
        assert "hello" in lines
        assert "world" in lines

    @pytest.mark.asyncio
    async def test_runs_in_workspace(self, fs: FileSystem, workspace: Path):
        """Executes commands with cwd set to workspace."""
        stream = await fs.bash("pwd")
        output = ""
        async for line in stream:
            output += line
        assert output.strip() == str(workspace)

    @pytest.mark.asyncio
    async def test_background_returns_dict(self, fs: FileSystem):
        """Background mode returns result dict."""
        result = await fs.bash("echo hello", run_in_background=True)
        assert result["exit_code"] == 0
        assert "hello" in result["stdout"]

    @pytest.mark.asyncio
    async def test_background_captures_stderr(self, fs: FileSystem):
        """Background mode captures stderr separately."""
        result = await fs.bash("echo err >&2", run_in_background=True)
        assert "err" in result["stderr"]

    @pytest.mark.asyncio
    async def test_background_timeout(self, fs: FileSystem):
        """Background mode returns timeout error."""
        result = await fs.bash("sleep 10", timeout=1, run_in_background=True)
        assert result["exit_code"] == -1
        assert "timed out" in result["stderr"]

    @pytest.mark.asyncio
    async def test_blocked_apt(self, fs: FileSystem):
        """Blocks apt when allow_system_install is False."""
        with pytest.raises(PermissionError, match="System install commands are blocked"):
            await fs.bash("apt install something")

    @pytest.mark.asyncio
    async def test_blocked_sudo(self, fs: FileSystem):
        """Blocks sudo when allow_system_install is False."""
        with pytest.raises(PermissionError, match="System install commands are blocked"):
            await fs.bash("sudo rm -rf /")

    @pytest.mark.asyncio
    async def test_allowed_with_flag(self, workspace: Path):
        """Allows system commands when allow_system_install is True."""
        fs = FileSystem(str(workspace), allow_system_install=True)
        # Should not raise, just check command validation passes.
        fs._check_command("apt install something")

    @pytest.mark.asyncio
    async def test_nonzero_exit_code(self, fs: FileSystem):
        """Captures non-zero exit codes in background mode."""
        result = await fs.bash("exit 1", run_in_background=True)
        assert result["exit_code"] == 1

    @pytest.mark.asyncio
    async def test_empty_command(self, fs: FileSystem):
        """Raises ValueError for empty command."""
        with pytest.raises(ValueError, match="Empty command"):
            await fs.bash("")
