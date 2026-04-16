"""Bash tools for workspace operations.

- bash: Execute shell commands
- grep_search: Search file contents with regex
- glob_search: Find files by glob pattern
"""

from langchain.tools import tool
from langgraph.prebuilt import ToolRuntime
from langgraph.types import Command


@tool(name_or_callable="bash", description="TODO")
async def bash(command: str, tool_runtime: ToolRuntime, timeout: int = 120) -> Command:
    """Execute a shell command in the workspace."""
    # TODO: implement
    return Command(update={"messages": []})


@tool(name_or_callable="grep_search", description="TODO")
async def grep_search(
    pattern: str,
    tool_runtime: ToolRuntime,
    path: str = ".",
    glob: str | None = None,
    file_type: str | None = None,
    after: int = 0,
    before: int = 0,
    context: int = 0,
) -> Command:
    """Search file contents with regex."""
    # TODO: implement
    return Command(update={"messages": []})


@tool(name_or_callable="glob_search", description="TODO")
async def glob_search(
    pattern: str,
    tool_runtime: ToolRuntime,
    path: str = ".",
) -> Command:
    """Find files matching a glob pattern."""
    # TODO: implement
    return Command(update={"messages": []})


BASH_TOOLS: list = [bash, grep_search, glob_search]
