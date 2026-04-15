from langchain.tools import tool
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import ToolRuntime
from langgraph.types import Command

from agentic_patterns.shared.todos import update_todos
from agentic_patterns.subagent_pattern.prompts import (
    CREATE_FILE_DESCRIPTION,
)
from agentic_patterns.subagent_pattern.state import AgentState, ContextSchema


@tool(name_or_callable="create_file", description=CREATE_FILE_DESCRIPTION)
def create_file(file_name: str, content: str, tool_runtime: ToolRuntime[ContextSchema, AgentState]) -> Command:
    """Creates a file with the given name and content. In memory file system."""

    if tool_runtime.store is None:
        raise RuntimeError("Store is required for create_file tool")

    namespace = (tool_runtime.context.agent_name, "filesystems")
    thread_id = str(tool_runtime.config.get("thread_id", ""))
    tool_runtime.store.put(namespace=namespace, key=thread_id, value={file_name: content})

    return Command(
        update={
            "messages": [
                ToolMessage(
                    content=f"File '{file_name}' created successfully.",
                    tool_call_id=tool_runtime.tool_call_id,
                )
            ]
        }
    )


TOOLS = [create_file, update_todos]
