"""Tests for FileSystem class."""

import pytest

from tools.filesystem import FileSystem


class TestInit:
    """Tests for __init__."""

    def test_valid_workspace(self, workspace):
        """Initializes with a valid directory."""
        fs = FileSystem(str(workspace))
        assert fs.workspace == workspace
        assert fs.allow_system_install is False

    def test_allow_system_install_flag(self, workspace):
        """Respects allow_system_install flag."""
        fs = FileSystem(str(workspace), allow_system_install=True)
        assert fs.allow_system_install is True

    def test_invalid_workspace(self):
        """Raises ValueError for non-existent directory."""
        with pytest.raises(ValueError, match="does not exist"):
            FileSystem("/nonexistent/path")


class TestSafePath:
    """Tests for _safe_path."""

    def test_relative_path(self, fs, workspace):
        """Resolves relative paths inside workspace."""
        assert fs._safe_path("hello.txt") == workspace / "hello.txt"

    def test_nested_path(self, fs, workspace):
        """Resolves nested paths inside workspace."""
        assert fs._safe_path("subdir/nested.txt") == workspace / "subdir" / "nested.txt"

    def test_traversal_blocked(self, fs):
        """Blocks directory traversal attempts."""
        with pytest.raises(PermissionError, match="escapes workspace"):
            fs._safe_path("../../etc/passwd")

    def test_symlink_escape_blocked(self, fs, workspace):
        """Blocks symlinks that point outside workspace."""
        outside = workspace.parent / "outside"
        outside.mkdir()
        (workspace / "sneaky_link").symlink_to(outside)
        with pytest.raises(PermissionError, match="escapes workspace"):
            fs._safe_path("sneaky_link/file.txt")


class TestRead:
    """Tests for read method."""

    @pytest.mark.asyncio
    async def test_read_full_file(self, fs):
        """Reads entire file content."""
        content = await fs.read("hello.txt")
        assert content == "line1\nline2\nline3\nline4\nline5\n"

    @pytest.mark.asyncio
    async def test_read_with_offset(self, fs):
        """Reads from a specific line offset."""
        content = await fs.read("hello.txt", offset=2)
        assert content == "line3\nline4\nline5\n"

    @pytest.mark.asyncio
    async def test_read_with_limit(self, fs):
        """Reads limited number of lines."""
        content = await fs.read("hello.txt", limit=2)
        assert content == "line1\nline2\n"

    @pytest.mark.asyncio
    async def test_read_with_offset_and_limit(self, fs):
        """Reads with both offset and limit."""
        content = await fs.read("hello.txt", offset=1, limit=2)
        assert content == "line2\nline3\n"

    @pytest.mark.asyncio
    async def test_read_nested_file(self, fs):
        """Reads files in subdirectories."""
        content = await fs.read("subdir/nested.txt")
        assert content == "nested content\n"

    @pytest.mark.asyncio
    async def test_read_nonexistent(self, fs):
        """Raises FileNotFoundError for missing files."""
        with pytest.raises(FileNotFoundError, match="File not found"):
            await fs.read("nope.txt")

    @pytest.mark.asyncio
    async def test_read_traversal_blocked(self, fs):
        """Blocks reading files outside workspace."""
        with pytest.raises(PermissionError):
            await fs.read("../../etc/passwd")


class TestWrite:
    """Tests for write method."""

    @pytest.mark.asyncio
    async def test_write_new_file(self, fs, workspace):
        """Creates a new file with content."""
        await fs.write("new.txt", "hello world")
        assert (workspace / "new.txt").read_text() == "hello world"

    @pytest.mark.asyncio
    async def test_write_overwrite(self, fs, workspace):
        """Overwrites existing file content."""
        await fs.write("hello.txt", "replaced")
        assert (workspace / "hello.txt").read_text() == "replaced"

    @pytest.mark.asyncio
    async def test_write_missing_parent_raises(self, fs):
        """Raises FileNotFoundError when parent directory doesn't exist."""
        with pytest.raises(FileNotFoundError, match="Parent directory does not exist"):
            await fs.write("nonexistent/dir/file.txt", "data")

    @pytest.mark.asyncio
    async def test_write_returns_path(self, fs, workspace):
        """Returns the absolute path of the written file."""
        result = await fs.write("out.txt", "data")
        assert result == str(workspace / "out.txt")

    @pytest.mark.asyncio
    async def test_write_traversal_blocked(self, fs):
        """Blocks writing files outside workspace."""
        with pytest.raises(PermissionError):
            await fs.write("../../evil.txt", "bad")


class TestEdit:
    """Tests for edit method."""

    @pytest.mark.asyncio
    async def test_edit_single_replace(self, fs, workspace):
        """Replaces a unique string in the file."""
        await fs.edit("hello.txt", "line3", "replaced3")
        assert "replaced3" in (workspace / "hello.txt").read_text()

    @pytest.mark.asyncio
    async def test_edit_multiple_blocked(self, fs, workspace):
        """Raises ValueError when multiple occurrences exist without replace_all."""
        (workspace / "dupes.txt").write_text("aaa bbb aaa")
        with pytest.raises(ValueError, match="Multiple occurrences"):
            await fs.edit("dupes.txt", "aaa", "ccc")

    @pytest.mark.asyncio
    async def test_edit_replace_all(self, fs, workspace):
        """Replaces all occurrences when replace_all is True."""
        (workspace / "dupes.txt").write_text("aaa bbb aaa")
        await fs.edit("dupes.txt", "aaa", "ccc", replace_all=True)
        assert (workspace / "dupes.txt").read_text() == "ccc bbb ccc"

    @pytest.mark.asyncio
    async def test_edit_string_not_found(self, fs):
        """Raises ValueError when old_string doesn't exist in file."""
        with pytest.raises(ValueError, match="String not found"):
            await fs.edit("hello.txt", "nonexistent", "new")

    @pytest.mark.asyncio
    async def test_edit_nonexistent_file(self, fs):
        """Raises FileNotFoundError for missing files."""
        with pytest.raises(FileNotFoundError, match="File not found"):
            await fs.edit("nope.txt", "a", "b")

    @pytest.mark.asyncio
    async def test_edit_traversal_blocked(self, fs):
        """Blocks editing files outside workspace."""
        with pytest.raises(PermissionError):
            await fs.edit("../../etc/passwd", "root", "hacked")
