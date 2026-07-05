"""Generic agent_node — written once, used by every agent built on base_v2.

Everything that used to differ between per-agent nodes is now either:
  - carried on ``runtime.context`` (system_prompt)
  - carried on ``state`` (active_tools, resolved via registry)
  - parametrised by TypeVar bound (state/context shapes)

Ported from ``agentic_patterns/react_agent/nodes.py`` with two substitutions:
  1. ``REACT_AGENT_SYSTEM_PROMPT``  -> ``runtime.context.system_prompt``
  2. hardcoded ``TOOLS``            -> ``resolve(state["active_tools"])``
"""

from langchain_core.messages import AIMessageChunk, BaseMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime

from agentic_patterns.base.schemas import Context, State
from agentic_patterns.shared.helper import handle_message, pre_llm_processing
from agentic_patterns.shared.skill_registry import ESSENTIAL_TOOL_NAMES, resolve
from utils.llms import MODELS


async def agent_node(state: State, config: RunnableConfig, runtime: Runtime[Context]) -> dict:  # type: ignore[type-arg]
    """Shared inference loop — identical for every agent."""
    try:
        print("====> [agent_node] <====")
        message: str = state["message"]
        messages: list[BaseMessage] = list(state["messages"])
        messages = pre_llm_processing(message, messages)

        system_message = SystemMessage(content=runtime.context.system_prompt)

        tool_names: list[str] = state.get("active_tools") or ESSENTIAL_TOOL_NAMES
        tools = resolve(tool_names)

        print(f"[agent_node] Sending to LLM with context: {runtime.context}")
        base_llm = MODELS[runtime.context.model]  # type: ignore[index]
        llm = base_llm.bind_tools(tools)
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

        # TODO: POST-LLM compaction hook.
        #       runtime.context.compaction drives the strategy.
        #       Invariant: never drop the last tool_call / tool_result pair.

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
