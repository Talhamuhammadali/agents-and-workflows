"""Redis pub/sub for per-thread interrupt signals.

One channel per thread: `interrupt:{thread_id}`. The streaming endpoint runs
`listen_for_interrupt` concurrently with the agent; a separate HTTP call fires
`publish_interrupt`, which delivers a message on the channel and causes the
listener to return.

Pub/sub (not a key) because the signal is ephemeral — if no one is streaming
the thread, there's nothing to interrupt and the message is simply dropped.
"""

from redis.asyncio import Redis

from ui.backend.thread_store import redis_url


def _channel(thread_id: str) -> str:
    return f"interrupt:{thread_id}"


async def publish_interrupt(thread_id: str) -> int:
    """Fire an interrupt for `thread_id`. Returns the number of subscribers reached."""
    async with Redis.from_url(redis_url(), decode_responses=True) as r:
        return await r.publish(_channel(thread_id), "1")


async def listen_for_interrupt(thread_id: str) -> None:
    """Block until an interrupt arrives on this thread's channel, then return.

    Intended to race against the agent stream task. On cancellation the
    subscription is torn down cleanly by the async context managers.
    """
    async with Redis.from_url(redis_url(), decode_responses=True) as r:
        async with r.pubsub() as ps:
            await ps.subscribe(_channel(thread_id))
            async for msg in ps.listen():
                if msg.get("type") == "message":
                    return
