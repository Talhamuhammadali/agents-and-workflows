"""Node functions for the subagent pattern graph."""

from pprint import pprint

from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.prebuilt import ToolNode
from langgraph.runtime import Runtime

from agentic_patterns.subagent_pattern.prompts import MAIN_AGENT_SYSTEM_PROMPT
from agentic_patterns.subagent_pattern.state import AgentState, ContextSchema
from agentic_patterns.subagent_pattern.tools import TOOLS
from utils import MODELS

tool_node = ToolNode(tools=TOOLS)


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

    user_message = HumanMessage(content=message)
    messages = messages or []
    messages.append(user_message)
    return messages


def handle_message(
    message: AIMessage | AIMessageChunk | HumanMessage, internal: bool = False, agent_name: str | None = None
) -> BaseMessage:
    """Handle incoming messages from the LLM stream."""
    additional_kwargs = {"internal": internal}
    message.name = agent_name
    message.additional_kwargs = {**message.additional_kwargs, **additional_kwargs}
    return message


def agent_node(state: AgentState, runtime: Runtime[ContextSchema]) -> dict:  # type: ignore[type-arg]
    """Invoke the llm with pre and post llm processing."""
    try:
        print("====> [agent_node] <====")
        message: str = state["message"]
        messages: list[BaseMessage] = list(state.get("messages", []))
        messages = pre_llm_processing(message, messages)
        system_message = SystemMessage(content=MAIN_AGENT_SYSTEM_PROMPT)

        print(f"[agent_node] Sending to LLM with context: {runtime.context}")
        base_llm = MODELS[runtime.context.model]  # type: ignore[index]
        llm = base_llm.bind_tools(TOOLS)
        ai_message: AIMessageChunk | None = None

        for chunk in llm.stream([system_message, *messages]):
            if not isinstance(chunk, AIMessageChunk):
                continue
            ai_message = chunk if ai_message is None else ai_message + chunk  # type: ignore[assignment]
            runtime.stream_writer(handle_message(chunk, agent_name=runtime.context.agent_name))

        if ai_message is not None:
            enriched_message = handle_message(ai_message, agent_name=runtime.context.agent_name)
            messages.append(enriched_message)
        pprint(enriched_message.model_dump(), indent=2)
        return {"messages": messages}
    except Exception as e:
        print(f"[agent_node] Error: {e}")
        raise


# TODO 4: Define the subagent node
def subagent_node(state: AgentState, runtime: Runtime[ContextSchema]) -> dict:  # type: ignore[type-arg]
    """Delegate work to a subagent (a separate compiled graph)."""
    # Invoke the subagent graph with relevant context
    # Return the subagent's response as messages
    raise NotImplementedError


# TODO 5: Define the router function
def route_llm_output(state: AgentState, runtime: Runtime[ContextSchema]) -> str:
    """Route based on the last LLM message.

    Returns:
        "tools" - if LLM called a tool
        "subagents" - if LLM wants to delegate to a subagent
        "__end__" - if LLM is done (final text response)
    """
    last_message = state.get("messages", [])[-1]
    # if last_message.tool_calls and any(call.get("tool_name") == "subagent" for call in last_message.tool_calls):
    #     return "subagents"
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        print(f"Tool calls detected: {[call.get('name') for call in last_message.tool_calls]}")
        return "tools"
    return "turn_end"
