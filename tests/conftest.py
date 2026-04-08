"""Shared fixtures for tests."""

import pytest

from tools.filesystem import FileSystem


@pytest.fixture
def workspace(tmp_path):
    """Create a temporary workspace with sample files."""
    (tmp_path / "hello.txt").write_text("line1\nline2\nline3\nline4\nline5\n")
    (tmp_path / "app.py").write_text("import os\n\ndef main():\n    print('hello')\n    return 0\n")
    (tmp_path / "utils.py").write_text("def helper():\n    pass\n\ndef another_helper():\n    pass\n")
    (tmp_path / "config.json").write_text('{"key": "value"}\n')
    (tmp_path / "subdir").mkdir()
    (tmp_path / "subdir" / "nested.txt").write_text("nested content\n")
    (tmp_path / "subdir" / "module.py").write_text("def sub_func():\n    print('sub')\n")
    return tmp_path


@pytest.fixture
def fs(workspace):
    """Create a FileSystem instance scoped to the workspace."""
    return FileSystem(str(workspace))
