"""Tools for working with the workspace in a linux filesystem.

File CRUD tools:
  - read_file: Read file contents with optional offset/limit
  - write_file: Create or overwrite a file
  - edit_file: Find-and-replace text in a file

Bash tools (TODO):
  - bash: Execute shell commands
  - grep_search: Search file contents with regex
  - glob_search: Find files by glob pattern
"""

from langchain.tools import tool
from langgraph.prebuilt import ToolRuntime
from langgraph.types import Command

from agentic_patterns.shared.helper import (
    find_last_file_interaction,
    format_cat_n,
    generate_diff,
    get_filesystem,
    tool_reply,
)
from agentic_patterns.shared.prompts.workspace_prompts import (
    EDIT_FILE_DESCRIPTION,
    READ_FILE_DESCRIPTION,
    WRITE_FILE_DESCRIPTION,
)


@tool(name_or_callable="write_file", description=WRITE_FILE_DESCRIPTION)
async def write_file(path: str, content: str, tool_runtime: ToolRuntime) -> Command:
    """Create or overwrite a file in the workspace."""
    fs = get_filesystem(tool_runtime)

    try:
        await fs.write(path, content)
        key = "write_success"
    except FileNotFoundError:
        key = "write_error_no_parent"
    except PermissionError:
        key = "write_error_permission"

    return tool_reply(tool_runtime, key, path=path)


@tool(name_or_callable="edit_file", description=EDIT_FILE_DESCRIPTION)
async def edit_file(
    path: str,
    old_string: str,
    new_string: str,
    tool_runtime: ToolRuntime,
    replace_all: bool = False,
) -> Command:
    """Find and replace text in a file."""
    fs = get_filesystem(tool_runtime)
    try:
        content = await fs.read(path)
    except FileNotFoundError:
        return tool_reply(tool_runtime, "edit_error_not_found", path=path)
    except PermissionError:
        return tool_reply(tool_runtime, "edit_error_permission", path=path)

    if old_string not in content:
        return tool_reply(tool_runtime, "edit_error_string_not_found", path=path)

    if not replace_all and content.count(old_string) > 1:
        return tool_reply(tool_runtime, "edit_error_multiple", path=path)

    await fs.edit(path, old_string, new_string, replace_all=replace_all)
    after = content.replace(old_string, new_string) if replace_all else content.replace(old_string, new_string, 1)
    diff = generate_diff(content, after, path)
    return tool_reply(tool_runtime, "edit_success", path=path, diff=diff)


@tool(name_or_callable="read_file", description=READ_FILE_DESCRIPTION)
async def read_file(
    tool_runtime: ToolRuntime,
    path: str,
    offset: int = 0,
    limit: int = 2000,
    force: bool = False,
) -> Command:
    """Read file contents with optional offset and limit."""
    fs = get_filesystem(tool_runtime)

    try:
        content = await fs.read(path, offset=offset, limit=limit)
    except FileNotFoundError:
        return tool_reply(tool_runtime, "read_error_not_found", path=path)
    except PermissionError:
        return tool_reply(tool_runtime, "read_error_permission", path=path)

    if not force:
        messages = (tool_runtime.state or {}).get("messages") or []
        last = find_last_file_interaction(path, messages)
        if last is not None:
            return tool_reply(tool_runtime, "read_unchanged", path=path)

    return tool_reply(tool_runtime, "read_success", content=format_cat_n(content))


FILE_TOOLS: list = [write_file, edit_file, read_file]
