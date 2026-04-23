"""Thread persistence and state loading helpers.

Redis layout for the thread registry:
- `ui:thread_ids`       — sorted set scored by updated_at_ms (ZREVRANGE = newest first)
- `ui:thread:{id}`      — JSON ThreadMeta doc

Checkpointer state (messages, todos, ...) is owned by LangGraph's AsyncRedisSaver
and fetched via `load_agent_state` / deleted via `delete_agent_thread`.
"""

import json
import os
from datetime import UTC, datetime

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.redis import AsyncRedisSaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.store.redis import AsyncRedisStore
from langgraph.types import StateSnapshot
from redis.asyncio import Redis
from uuid_utils import uuid7

from agentic_patterns.base.schemas import Context, State
from agentic_patterns.data_agent_v2.agent import DATA_AGENT_V2_BUILDER
from ui.backend.models import AgentStateResponse, PendingInterrupt, ThreadMeta

THREAD_INDEX_KEY = "ui:thread_ids"


def redis_url() -> str:
    return os.environ.get("REDIS_URL", "redis://localhost:6379/0")


def _thread_key(thread_id: str) -> str:
    return f"ui:thread:{thread_id}"


def _now() -> tuple[str, int]:
    dt = datetime.now(UTC)
    return dt.isoformat(), int(dt.timestamp() * 1000)


async def get_latest_snapshot(
    agent: CompiledStateGraph[State, Context, State, State], config: RunnableConfig
) -> StateSnapshot | None:
    """Return the head StateSnapshot for this thread, or None if there's no history."""
    history = [snap async for snap in agent.aget_state_history(config)]
    return history[0] if history else None


async def load_agent_state(thread_id: str) -> AgentStateResponse:
    """Fetch the latest checkpointer state + any pending interrupts for a thread."""
    async with AsyncRedisStore.from_conn_string(redis_url()) as store:
        await store.setup()
        async with AsyncRedisSaver.from_conn_string(redis_url()) as ch:
            await ch.asetup()
            agent = DATA_AGENT_V2_BUILDER.compile(store=store, checkpointer=ch)
            config = RunnableConfig(configurable={"thread_id": thread_id})
            snapshot = await get_latest_snapshot(agent, config)
            if not snapshot:
                return AgentStateResponse(values={})
            pending = [PendingInterrupt(id=i.id, value=i.value) for i in snapshot.interrupts]
            return AgentStateResponse(values=dict(snapshot.values or {}), pending_interrupts=pending)


async def delete_agent_thread(thread_id: str) -> None:
    """Drop the checkpointer's record of a thread."""
    async with AsyncRedisSaver.from_conn_string(redis_url()) as ch:
        await ch.asetup()
        await ch.adelete_thread(thread_id)


async def create_thread(title: str | None) -> ThreadMeta:
    """Register a new thread in Redis and return its metadata."""
    thread_id = str(uuid7())
    iso, score = _now()
    meta = ThreadMeta(thread_id=thread_id, title=title or "New chat", updated_at=iso)
    async with Redis.from_url(redis_url(), decode_responses=True) as r:
        pipe = r.pipeline()
        pipe.set(_thread_key(thread_id), meta.model_dump_json())
        pipe.zadd(THREAD_INDEX_KEY, {thread_id: score})
        await pipe.execute()
    return meta


async def list_threads() -> list[ThreadMeta]:
    """Return threads newest-first from the Redis registry."""
    async with Redis.from_url(redis_url(), decode_responses=True) as r:
        ids = await r.zrevrange(THREAD_INDEX_KEY, 0, -1)
        if not ids:
            return []
        docs = await r.mget([_thread_key(i) for i in ids])
    return [ThreadMeta(**json.loads(d)) for d in docs if d]


async def delete_thread(thread_id: str) -> None:
    """Remove a thread from the registry AND from the checkpointer."""
    async with Redis.from_url(redis_url(), decode_responses=True) as r:
        pipe = r.pipeline()
        pipe.zrem(THREAD_INDEX_KEY, thread_id)
        pipe.delete(_thread_key(thread_id))
        await pipe.execute()
    await delete_agent_thread(thread_id)
