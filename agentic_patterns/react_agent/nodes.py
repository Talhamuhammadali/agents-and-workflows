"""Fixed graph nodes for react agent."""

from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime

from agentic_patterns.react_agent.prompts import REACT_AGENT_SYSTEM_PROMPT
from agentic_patterns.react_agent.state import ReactAgentContextSchema, ReactAgentState
from agentic_patterns.react_agent.tools import TOOLS
from agentic_patterns.shared.helper import handle_message, pre_llm_processing
from utils.llms import MODELS


async def agent_node(state: ReactAgentState, config: RunnableConfig, runtime: Runtime[ReactAgentContextSchema]) -> dict:  # type: ignore[type-arg]
    """Invoke the llm with pre and post llm processing."""
    try:
        print("====> [agent_node] <====")
        message: str = state.get("message", "No message provided")
        messages: list[BaseMessage] = list(state.get("messages", []))
        messages = pre_llm_processing(message, messages)
        system_message = SystemMessage(content=REACT_AGENT_SYSTEM_PROMPT)

        print(f"[agent_node] Sending to LLM with context: {runtime.context.workspace}")
        base_llm = MODELS[runtime.context.model]  # type: ignore[index]
        llm = base_llm.bind_tools(TOOLS)
        ai_message: AIMessageChunk | None = None

        async for chunk in llm.astream([system_message, *messages]):
            if not isinstance(chunk, AIMessageChunk):
                continue

            if isinstance(chunk.content, str):
                # gemini 2.5 patch
                if (
                    chunk.response_metadata.get("stop_reason") in ["end_turn", "tool_use"]
                    or chunk.chunk_position == "last"
                ):
                    continue

                print(f"[agent_node] Received str text chunk: {chunk.content}")
                last_block = ai_message.content_blocks[-1] if ai_message and ai_message.content_blocks else None
                if last_block:
                    new_block = {**last_block}
                    block_type = str(new_block.get("type", "text"))
                    new_block[block_type] = chunk.content
                    chunk.content = [new_block]
                else:
                    chunk.content = [{"type": "text", "text": chunk.content, "index": 0}]

            ai_message = chunk if ai_message is None else ai_message + chunk
            runtime.stream_writer(handle_message(chunk.model_copy(deep=True), agent_name=runtime.context.agent_name))

        if ai_message is not None:
            enriched_message = handle_message(ai_message, agent_name=runtime.context.agent_name)
            # Last message in state is always the user message, so we append the new ai message after it.
            return {"messages": [messages[-1], enriched_message] if messages else [enriched_message]}
        else:
            print("[agent_node] No AIMessage received from LLM.")
            raise ValueError("LLM did not return any message.")
    except Exception as e:
        print(f"[agent_node] Error: {e}")
        raise e


async def router(state: ReactAgentState) -> str:
    """Route the LLM output to the appropriate next node."""
    last_message = state.get("messages", [])[-1]

    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"
    else:
        return "end"
