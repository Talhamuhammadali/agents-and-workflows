"""Shared tool giving the agent the ability to ask the user a question and get a response."""
from langchain.tools import tool
from langgraph.prebuilt import ToolRuntime
from langgraph.types import Command, interrupt
from pydantic import BaseModel, Field

from agentic_patterns.shared.helper import tool_reply
from agentic_patterns.shared.prompts.ask_prompts import ASK_TOOL_DESCRIPTION

OPEN_ENDED_OPTION = "Something else (please specify)"


class Question(BaseModel):
    """A single question to ask the user."""
    question: str = Field(..., description="The question to ask the user. Should be specific and clear.")
    options: list[str] | None = Field(None, description="Optional list of options for multiple choice questions.")


def _with_open_ended(q: Question) -> dict:
    data = q.model_dump()
    if data.get("options"):
        data["options"] = [*data["options"], OPEN_ENDED_OPTION]
    return data


@tool("Ask", description=ASK_TOOL_DESCRIPTION)
async def ask_question(questions: list[Question], tool_runtime: ToolRuntime) -> Command:
    """Post questions to the user and return their answer as the tool result."""
    response = interrupt([_with_open_ended(q) for q in questions])
    return tool_reply(tool_runtime, "ask_question", answer=response)
