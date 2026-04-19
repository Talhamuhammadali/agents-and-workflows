"""Convert LangChain chunks and persisted messages into MessageResponse events.

- `chunk_to_events`    — live SSE streaming from agent.astream().
- `messages_to_events` — rehydrate persisted BaseMessage[] from the checkpointer.
- `sse_event_stream`   — async generator producing SSE-formatted strings for one turn.

All share `parent_run_id` as the outer merge key so the UI accumulator groups
one agent turn into a single AI block. Tool results key on `tool_call_id` so
the UI correlates each result back to its originating call.
"""

from pathlib import Path
from typing import AsyncIterator

from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    HumanMessage,
    ToolMessage,
    ToolMessageChunk,
)
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.redis import AsyncRedisSaver
from langgraph.store.redis import AsyncRedisStore
from uuid_utils import uuid7

from agentic_patterns.react_agent.agent import REACT_AGENT_BUILDER
from agentic_patterns.react_agent.state import ReactAgentContextSchema
from ui.backend.event_helpers import ai_content_events, as_text, now_iso, tool_result_event
from ui.backend.models import MessageResponse, MessageTypes
from ui.backend.thread_store import redis_url
from utils.llms import Model


def chunk_to_events(
    chunk: AIMessageChunk | ToolMessageChunk,
    thread_id: str,
    parent_run_id: str,
) -> list[MessageResponse]:
    """Fan a single stream chunk out into zero or more MessageResponse events."""
    ts = now_iso()

    if isinstance(chunk, ToolMessageChunk):
        if not chunk.content:
            return []
        return [tool_result_event(str(chunk.content), chunk.tool_call_id or "", thread_id, ts, chunk.name)]

    if not isinstance(chunk, AIMessageChunk):
        return []

    return ai_content_events(chunk.content, chunk.tool_calls, thread_id, parent_run_id, ts, chunk.name)


def messages_to_events(messages: list[BaseMessage], thread_id: str) -> list[MessageResponse]:
    """Rehydrate persisted BaseMessage[] into a flat MessageResponse[].

    Turn boundary: each HumanMessage rotates `parent_run_id` so the UI renders
    one AI block per turn.
    """
    events: list[MessageResponse] = []
    parent_run_id = str(uuid7())
    ts = now_iso()

    for msg in messages:
        if isinstance(msg, HumanMessage):
            parent_run_id = str(uuid7())
            events.append(
                MessageResponse(
                    id=msg.id or str(uuid7()), thread_id=thread_id, checkpoint_id=None,
                    message_type=MessageTypes.TEXT, role_type="human", subtype=None,
                    content=as_text(msg.content), name=None, timestamp=ts,
                )
            )
        elif isinstance(msg, AIMessage):
            events.extend(
                ai_content_events(msg.content, msg.tool_calls, thread_id, parent_run_id, ts, msg.name)
            )
        elif isinstance(msg, ToolMessage):
            events.append(
                tool_result_event(as_text(msg.content), msg.tool_call_id or "", thread_id, ts, msg.name)
            )

    return events


async def sse_event_stream(thread_id: str, message: str) -> AsyncIterator[str]:
    """Run one agent turn and yield SSE-formatted MessageResponse events."""
    parent_run_id = f"run-{uuid7()}"
    async with AsyncRedisStore.from_conn_string(redis_url()) as store:
        await store.setup()
        async with AsyncRedisSaver.from_conn_string(redis_url()) as ch:
            await ch.asetup()
            agent = REACT_AGENT_BUILDER.compile(store=store, checkpointer=ch)
            context = ReactAgentContextSchema(
                workspace=Path("tests/workspaces/sandbox").resolve(),
                agent_name="ReactAgent",
                model=Model.VERTEX_GEMINI_2_5.value,
            )
            config = RunnableConfig(configurable={"thread_id": thread_id})
            async for chunk in agent.astream(
                {"message": message}, context=context, config=config,
                stream_mode=["custom"], version="v2",
            ):  # type: ignore[call-overload]
                for event in chunk_to_events(chunk["data"], thread_id, parent_run_id):
                    yield f"data: {event.model_dump_json()}\n\n"
