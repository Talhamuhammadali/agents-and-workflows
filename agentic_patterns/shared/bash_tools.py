"""Bash tools for workspace operations.

- bash: Execute shell commands
- grep_search: Search file contents with regex
- glob_search: Find files by glob pattern
"""

import re
from collections.abc import AsyncGenerator
from typing import cast

from langchain.tools import tool
from langchain_core.messages import HumanMessage, ToolMessageChunk
from langchain_core.messages.utils import count_tokens_approximately
from langgraph.config import get_stream_writer
from langgraph.prebuilt import ToolRuntime
from langgraph.types import Command

from agentic_patterns.shared.helper import format_grep_results, get_filesystem, handle_message, tool_reply
from agentic_patterns.shared.prompts.bash_prompts import (
    BASH_DESCRIPTION,
    GLOB_SEARCH_DESCRIPTION,
    GREP_SEARCH_DESCRIPTION,
)

MAX_BASH_TOKENS = 10_000


@tool(name_or_callable="bash", description=BASH_DESCRIPTION)
async def bash(command: str, tool_runtime: ToolRuntime, timeout: int = 120) -> Command:
    """Execute a shell command in the workspace, streaming output to the UI."""
    if not command.strip():
        return tool_reply(tool_runtime, "bash_error_empty")

    fs = get_filesystem(tool_runtime)

    try:
        stream = cast(AsyncGenerator[str, None], await fs.bash(command, timeout=timeout))
    except PermissionError as exc:
        return tool_reply(tool_runtime, "bash_error_blocked", reason=str(exc))
    except ValueError:
        return tool_reply(tool_runtime, "bash_error_empty")

    writer = get_stream_writer()
    agent_name = getattr(tool_runtime.context, "agent_name", None)
    tool_call_id = tool_runtime.tool_call_id or ""
    chunks: list[str] = []

    async for chunk in stream:
        chunks.append(chunk)
        tool_chunk = ToolMessageChunk(content=chunk, tool_call_id=tool_call_id)
        writer(handle_message(tool_chunk, agent_name=agent_name))

    output = "".join(chunks)
    token_count = count_tokens_approximately([HumanMessage(content=output)])
    if token_count > MAX_BASH_TOKENS:
        # Preserve tail: approximate chars to keep based on token ratio.
        keep_chars = max(1, int(len(output) * (MAX_BASH_TOKENS / token_count)))
        return tool_reply(tool_runtime, "bash_truncated", max_tokens=MAX_BASH_TOKENS, output=output[-keep_chars:])

    return tool_reply(tool_runtime, "bash_success", output=output)


@tool(name_or_callable="grep_search", description=GREP_SEARCH_DESCRIPTION)
async def grep_search(
    pattern: str,
    tool_runtime: ToolRuntime,
    path: str = ".",
    glob: str | None = None,
    file_type: str | None = None,
    output_mode: str = "files_with_matches",
    after: int = 0,
    before: int = 0,
    context: int = 0,
    case_insensitive: bool = False,
    multiline: bool = False,
    show_line_numbers: bool = True,
    head_limit: int = 250,
    offset: int = 0,
) -> Command:
    """Search file contents with regex."""
    fs = get_filesystem(tool_runtime)

    try:
        results = await fs.grep(
            pattern,
            path=path,
            glob=glob,
            file_type=file_type,
            output_mode=output_mode,
            after=after,
            before=before,
            context=context,
            case_insensitive=case_insensitive,
            multiline=multiline,
            show_line_numbers=show_line_numbers,
            head_limit=head_limit,
            offset=offset,
        )
    except re.error as exc:
        return tool_reply(tool_runtime, "grep_error_invalid_regex", pattern=pattern, reason=str(exc))
    except FileNotFoundError:
        return tool_reply(tool_runtime, "search_error_not_found", path=path)
    except PermissionError:
        return tool_reply(tool_runtime, "search_error_permission", path=path)

    if not results:
        return tool_reply(tool_runtime, "search_no_matches", pattern=pattern, path=path)

    output = format_grep_results(results, output_mode)
    token_count = count_tokens_approximately([HumanMessage(content=output)])
    if token_count > MAX_BASH_TOKENS:
        keep_chars = max(1, int(len(output) * (MAX_BASH_TOKENS / token_count)))
        return tool_reply(tool_runtime, "bash_truncated", max_tokens=MAX_BASH_TOKENS, output=output[-keep_chars:])
    return tool_reply(tool_runtime, "bash_success", output=output)


@tool(name_or_callable="glob_search", description=GLOB_SEARCH_DESCRIPTION)
async def glob_search(
    pattern: str,
    tool_runtime: ToolRuntime,
    path: str = ".",
    limit: int = 200,
) -> Command:
    """Find files matching a glob pattern."""
    fs = get_filesystem(tool_runtime)

    try:
        matches = await fs.glob(pattern, path=path, limit=limit)
    except FileNotFoundError:
        return tool_reply(tool_runtime, "search_error_not_found", path=path)
    except PermissionError:
        return tool_reply(tool_runtime, "search_error_permission", path=path)

    if not matches:
        return tool_reply(tool_runtime, "search_no_matches", pattern=pattern, path=path)

    output = "\n".join(matches)
    token_count = count_tokens_approximately([HumanMessage(content=output)])
    if token_count > MAX_BASH_TOKENS:
        keep_chars = max(1, int(len(output) * (MAX_BASH_TOKENS / token_count)))
        return tool_reply(tool_runtime, "bash_truncated", max_tokens=MAX_BASH_TOKENS, output=output[-keep_chars:])
    return tool_reply(tool_runtime, "bash_success", output=output)


BASH_TOOLS: list = [bash, grep_search, glob_search]
