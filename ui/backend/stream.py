"""Convert LangChain chunks and persisted messages into MessageResponse events.

- `chunk_to_events`    — live SSE streaming from agent.astream().
- `messages_to_events` — rehydrate persisted BaseMessage[] from the checkpointer.
- `sse_event_stream`   — async generator producing SSE-formatted strings for one
                         turn, with Redis-signalled interrupt support.

All share `parent_run_id` as the outer merge key so the UI accumulator groups
one agent turn into a single AI block. Tool results key on `tool_call_id` so
the UI correlates each result back to its originating call.
"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import suppress
from pathlib import Path
from typing import Any

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
from langgraph.types import Command
from uuid_utils import uuid7

from agentic_patterns.data_agent_v2.agent import DATA_AGENT_V2_BUILDER
from agentic_patterns.data_agent_v2.prompts import DATA_AGENT_V2_SYSTEM_PROMPT
from agentic_patterns.data_agent_v2.state import DataAgentContext
from ui.backend.event_helpers import ai_content_events, as_text, now_iso, tool_result_event
from ui.backend.models import MessageResponse, MessageTypes
from ui.backend.pubsub import listen_for_interrupt
from ui.backend.thread_store import get_latest_snapshot, redis_url
from utils.llms import Model


def chunk_to_events(
    chunk: AIMessageChunk | ToolMessageChunk,
    thread_id: str,
    parent_run_id: str,
    tc_index_to_id: dict[int, str],
) -> list[MessageResponse]:
    """Fan a single stream chunk out into zero or more MessageResponse events."""
    ts = now_iso()

    if isinstance(chunk, ToolMessageChunk):
        if not chunk.content:
            return []
        return [tool_result_event(str(chunk.content), chunk.tool_call_id or "", thread_id, ts, chunk.name)]

    if not isinstance(chunk, AIMessageChunk):
        return []

    # Streaming path: emit partial args via tool_call_chunks, not tool_calls —
    # chunk.tool_calls rebuilds a (garbage) entry on every delta, causing dupes.
    return ai_content_events(
        chunk.content,
        tool_calls=None,
        tool_call_chunks=chunk.tool_call_chunks,
        thread_id=thread_id,
        parent_run_id=parent_run_id,
        ts=ts,
        name=chunk.name,
        tc_index_to_id=tc_index_to_id,
    )


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
                    id=msg.id or str(uuid7()),
                    thread_id=thread_id,
                    checkpoint_id=None,
                    message_type=MessageTypes.TEXT,
                    role_type="human",
                    subtype=None,
                    content=as_text(msg.content),
                    name=None,
                    timestamp=ts,
                )
            )
        elif isinstance(msg, AIMessage):
            events.extend(
                ai_content_events(
                    msg.content,
                    tool_calls=msg.tool_calls,
                    tool_call_chunks=None,
                    thread_id=thread_id,
                    parent_run_id=parent_run_id,
                    ts=ts,
                    name=msg.name,
                )
            )
        elif isinstance(msg, ToolMessage):
            events.append(tool_result_event(as_text(msg.content), msg.tool_call_id or "", thread_id, ts, msg.name))

    return events


async def sse_event_stream(thread_id: str, message: str | dict, model: Model) -> AsyncIterator[str]:
    """Streaming turn with Redis-signalled interrupt.

    Producer task drains `agent.astream` into an `asyncio.Queue`. The SSE
    generator body races `queue.get()` against a listener task subscribed to
    `interrupt:{thread_id}`. On interrupt we cancel the producer, patch the
    checkpointer state, and emit a final NOTIFICATION event.

    Queue/producer split maps 1:1 to a future worker container: swap the
    queue for a Redis Stream and the producer runs elsewhere.
    """
    parent_run_id = f"run-{uuid7()}"
    workspace = Path("sandbox").resolve()
    sentinel = object()

    async with AsyncRedisStore.from_conn_string(redis_url()) as store:
        await store.setup()
        async with AsyncRedisSaver.from_conn_string(redis_url()) as ch:
            await ch.asetup()
            agent = DATA_AGENT_V2_BUILDER.compile(store=store, checkpointer=ch)
            context = DataAgentContext(
                workspace=workspace,
                system_prompt=DATA_AGENT_V2_SYSTEM_PROMPT,
                agent_name="Data Agent",
                model=model.value,
            )
            config = RunnableConfig(configurable={"thread_id": thread_id})
            tc_index_to_id: dict[int, str] = {}
            queue: asyncio.Queue = asyncio.Queue()
            # finding pending interrupts before starting the producer
            snapshot = await get_latest_snapshot(agent, config)
            agent_inputs = {"context": context, "config": config, "version": "v2", "stream_mode": ["custom"]}

            if snapshot and snapshot.interrupts:
                print(f"Found pending interrupts for thread_id {thread_id}, using command input.")
                agent_inputs["input"] = Command(resume=message)
            else:
                agent_inputs["input"] = {
                    "message": message,
                    "messages": [HumanMessage(content=message if isinstance(message, str) else [message])],
                    "workspace": str(workspace),
                }

            # Accumulate AI chunks here so a mid-stream interrupt can inject to state
            partial_ai: AIMessageChunk | None = None

            async def produce() -> None:
                nonlocal partial_ai
                try:
                    async for chunk in agent.astream(**agent_inputs):  # type: ignore[call-overload]
                        data = chunk.get("data") if isinstance(chunk, dict) else None
                        if isinstance(data, AIMessageChunk):
                            # Reset only when a *new* id starts. Some providers (e.g. OpenAI)
                            # can emit continuation deltas with id=None — treat those as
                            # part of the current message, not a new one.
                            if partial_ai is None:
                                partial_ai = data
                            elif data.id and partial_ai.id and data.id != partial_ai.id:
                                partial_ai = data
                            else:
                                partial_ai = partial_ai + data
                        await queue.put(chunk)
                finally:
                    await queue.put(sentinel)

            producer = asyncio.create_task(produce())
            listener = asyncio.create_task(listen_for_interrupt(thread_id))
            interrupted = False

            try:
                while True:
                    get_task = asyncio.create_task(queue.get())
                    done, _ = await asyncio.wait({get_task, listener}, return_when=asyncio.FIRST_COMPLETED)
                    if listener in done:
                        get_task.cancel()
                        with suppress(asyncio.CancelledError):
                            await get_task
                        interrupted = True
                        break
                    chunk = get_task.result()
                    if chunk is sentinel:
                        break
                    for event in chunk_to_events(chunk["data"], thread_id, parent_run_id, tc_index_to_id):
                        yield f"data: {event.model_dump_json()}\n\n"
            finally:
                producer.cancel()
                with suppress(asyncio.CancelledError):
                    await producer
                if not listener.done():
                    listener.cancel()
                    with suppress(asyncio.CancelledError):
                        await listener

            if interrupted:
                await _patch_state_after_interrupt(agent, config, partial_ai)
                yield f"data: {_interrupted_event(thread_id).model_dump_json()}\n\n"


async def _patch_state_after_interrupt(
    agent: Any,
    config: RunnableConfig,
    partial_ai: AIMessageChunk | None = None,
) -> None:
    """Repair checkpointer state after a mid-turn cancel.

    Orphan tool_calls on the last AI message would 400 the next turn, so we
    satisfy them with synthetic ToolMessage(s). A bare AI message gets its
    content replaced via same-id write (the `add_messages` reducer merges on id).
    If nothing was committed yet (mid-stream cancel), commit the partial text —
    drop tool_call_chunks so malformed calls don't break the next turn.
    """
    snapshot = await agent.aget_state(config)
    messages = snapshot.values.get("messages", []) if snapshot and snapshot.values else []
    last = messages[-1] if messages else None
    interrupt_message = "**--- INTERRUPTED ---**"
    if isinstance(last, AIMessage) and last.tool_calls:
        tool_msgs = [
            ToolMessage(content=interrupt_message, tool_call_id=tc["id"], name=tc.get("name")) for tc in last.tool_calls
        ]
        await agent.aupdate_state(config, {"messages": tool_msgs})
    elif isinstance(last, AIMessage):
        await agent.aupdate_state(config, {"messages": [AIMessage(content=interrupt_message, id=last.id)]})
    elif partial_ai and isinstance(partial_ai.content, list):
        # Drop tool_use (would orphan and 400 next turn); append marker to last text block.
        blocks: list[Any] = [b for b in partial_ai.content if not (isinstance(b, dict) and b.get("type") == "tool_use")]
        for b in reversed(blocks):
            if isinstance(b, dict) and b.get("type") == "text":
                b["text"] = f"{b.get('text', '')}\n\n{interrupt_message}"
                break
        else:
            blocks.append({"type": "text", "text": interrupt_message})
        partial_ai.content = blocks
        partial_ai.tool_call_chunks = []
        await agent.aupdate_state(config, {"messages": [partial_ai]})
    else:
        await agent.aupdate_state(config, {"messages": [AIMessage(content=interrupt_message)]})


def _interrupted_event(thread_id: str) -> MessageResponse:
    return MessageResponse(
        id=f"interrupt-{uuid7()}",
        thread_id=thread_id,
        checkpoint_id=None,
        message_type=MessageTypes.NOTIFICATION,
        role_type="ai",
        subtype="interrupted",
        content="**--- INTERRUPTED ---**",
        name=None,
        timestamp=now_iso(),
    )
