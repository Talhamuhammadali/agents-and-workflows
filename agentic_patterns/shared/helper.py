from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, HumanMessage, ToolMessage


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
