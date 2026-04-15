"""Todos tool for managing a list of tasks. Provides functions to add, update, and clear todos.."""

from langchain.tools import tool
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import ToolRuntime
from langgraph.types import Command

from agentic_patterns.shared.prompts.todo_prompts import UPDATE_TODOS_DESCRIPTION


@tool(name_or_callable="update_todos", description=UPDATE_TODOS_DESCRIPTION)
def update_todos(todos: list[dict], tool_runtime: ToolRuntime) -> Command:
    """Replaces state.todos with the provided list. Each todo: {id, task, completed}."""
    return Command(
        update={
            "todos": todos,
            "messages": [
                ToolMessage(
                    content=f"Todos updated. {len(todos)} item(s) in list.",
                    tool_call_id=tool_runtime.tool_call_id,
                )
            ],
        }
    )
