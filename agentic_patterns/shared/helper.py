import difflib
import hashlib
from typing import Any, cast

from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, HumanMessage, ToolMessage, ToolMessageChunk
from langgraph.prebuilt import ToolRuntime
from langgraph.types import Command

from agentic_patterns.shared.prompts.ask_feedback import ASK_FEEDBACK
from agentic_patterns.shared.prompts.bash_feedback import BASH_FEEDBACK
from agentic_patterns.shared.prompts.workspace_feedback import FILE_FEEDBACK, SYSTEM_PREFIX
from helpers.filesystem import FileSystem

_FILE_TOOL_NAMES = frozenset({"read_file", "write_file"})
_FEEDBACK = {**FILE_FEEDBACK, **BASH_FEEDBACK, **ASK_FEEDBACK}


def feedback(key: str, **kwargs: Any) -> str:
    """Return a formatted feedback message for a given key and kwargs."""
    return _FEEDBACK[key].format(prefix=SYSTEM_PREFIX, **kwargs)


def format_grep_results(results: list[Any], output_mode: str) -> str:
    """Render grep results (list of str or dict) to plain text for the LLM."""
    if not results:
        return ""
    if output_mode == "files_with_matches":
        return "\n".join(cast(list[str], results))
    if output_mode == "count":
        return "\n".join(f"{r['file']}: {r['count']}" for r in results)
    # content mode
    blocks: list[str] = []
    for r in results:
        if "lines" in r:
            blocks.append(f"{r['file']}\n{r['lines']}")
        else:
            blocks.append(f"{r['file']}\t{r['match']}")
    return "\n--\n".join(blocks)


def pre_llm_processing(message: str, messages: list[BaseMessage]) -> list[BaseMessage]:
    """Process current message and message history before sending to LLM.

    This can include tasks like:
    - Message compaction
    - Fetching relevant documents
    - Adding system instructions
    """

    # TODO: Add prompt compaction explore trim_messages and related utilities in langchain
    if messages and isinstance(messages[-1], ToolMessage):
        return messages  # Don't add user message if last message is a tool call response still agents turn
    if messages and isinstance(messages[-1], HumanMessage):
        return messages  # Don't add user message if last message is a human message injected by langgraph.

    user_message = HumanMessage(content=message)
    messages = messages or []
    messages.append(user_message)
    return messages


def get_filesystem(tool_runtime: ToolRuntime) -> FileSystem:
    """Extract workspace from ToolRuntime context and return a FileSystem instance."""
    workspace = getattr(tool_runtime.context, "workspace", None)
    if workspace is None:
        raise RuntimeError("No workspace configured in agent context.")
    return FileSystem(workspace=str(workspace))


def content_hash(content: str) -> str:
    """Return a short md5 hex digest of content."""
    return hashlib.md5(content.encode()).hexdigest()


def tool_reply(
    tool_runtime: ToolRuntime,
    key: str,
    extra_messages: list[BaseMessage] | None = None,
    response_metadata: dict | None = None,
    **kwargs: Any,
) -> Command:
    """Build a Command with a ToolMessage from a feedback key, optionally followed by extra messages."""
    messages: list[BaseMessage] = [
        ToolMessage(
            content=feedback(key, **kwargs),
            tool_call_id=tool_runtime.tool_call_id,
            response_metadata=response_metadata or {},
        )
    ]
    if extra_messages:
        messages.extend(extra_messages)
    return Command(update={"messages": messages})


def find_last_file_hash(path: str, messages: list[BaseMessage]) -> str | None:
    """Walk messages backward, find the content hash from the last read/write ToolMessage for this path."""
    for msg in reversed(messages):
        if not isinstance(msg, ToolMessage):
            continue
        meta = msg.response_metadata or {}
        if meta.get("path") == path and meta.get("tool_name") in _FILE_TOOL_NAMES:
            return meta.get("content_hash")
    return None


def generate_diff(before: str, after: str, path: str, context_lines: int = 3) -> str:
    """Generate a unified diff between before and after content."""
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
            n=context_lines,
        )
    )


def format_cat_n(content: str) -> str:
    """Format file content with line numbers like cat -n."""
    lines = content.splitlines(keepends=True)
    return "".join(f"{i + 1}\t{line}" for i, line in enumerate(lines))


def handle_message(
    message: AIMessage | AIMessageChunk | HumanMessage | ToolMessageChunk,
    internal: bool = False,
    agent_name: str | None = None,
) -> BaseMessage:
    """Handle incoming messages from the LLM stream."""
    additional_kwargs = {"internal": internal}
    message.name = agent_name
    message.additional_kwargs = {**message.additional_kwargs, **additional_kwargs}
    return message
