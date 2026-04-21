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
from langchain_core.messages import HumanMessage
from langchain_core.messages.utils import count_tokens_approximately
from langgraph.prebuilt import ToolRuntime
from langgraph.types import Command

from agentic_patterns.shared.helper import (
    content_hash,
    find_last_file_hash,
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

MAX_READ_TOKENS = 20_000


@tool(name_or_callable="Write", description=WRITE_FILE_DESCRIPTION)
async def write_file(path: str, content: str, tool_runtime: ToolRuntime) -> Command:
    """Create or overwrite a file in the workspace."""
    fs = get_filesystem(tool_runtime)

    try:
        await fs.write(path, content)
        meta = {"path": path, "tool_name": "write_file", "content_hash": content_hash(content)}
        return tool_reply(tool_runtime, "write_success", response_metadata=meta, path=path)
    except FileNotFoundError:
        return tool_reply(tool_runtime, "write_error_no_parent", path=path)
    except PermissionError:
        return tool_reply(tool_runtime, "write_error_permission", path=path)


@tool(name_or_callable="Edit", description=EDIT_FILE_DESCRIPTION)
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


@tool(name_or_callable="Read", description=READ_FILE_DESCRIPTION)
async def read_file(
    tool_runtime: ToolRuntime,
    path: str,
    offset: int = 1,
    limit: int = 2000,
    force: bool = False,
) -> Command:
    """Read file contents with optional 1-indexed offset and limit."""
    fs = get_filesystem(tool_runtime)

    try:
        content = await fs.read(path, offset=max(0, offset - 1), limit=limit)
    except FileNotFoundError:
        return tool_reply(tool_runtime, "read_error_not_found", path=path)
    except PermissionError:
        return tool_reply(tool_runtime, "read_error_permission", path=path)

    token_count = count_tokens_approximately([HumanMessage(content=content)])
    if token_count > MAX_READ_TOKENS:
        return tool_reply(tool_runtime, "read_error_too_large", path=path, token_count=token_count)

    current_hash = content_hash(content)

    if not force:
        messages = (tool_runtime.state or {}).get("messages") or []
        last_hash = find_last_file_hash(path, messages)
        if last_hash is not None and last_hash == current_hash:
            return tool_reply(tool_runtime, "read_unchanged", path=path)

    meta = {"path": path, "tool_name": "read_file", "content_hash": current_hash}
    return tool_reply(tool_runtime, "read_success", response_metadata=meta, content=format_cat_n(content))


FILE_TOOLS: list = [write_file, edit_file, read_file]
