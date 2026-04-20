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

    Polls `get_message` instead of iterating `ps.listen()` — the latter holds
    an inner async generator that doesn't unwind cleanly when the task is
    cancelled mid-await, producing "aclose(): asynchronous generator is
    already running" on stream teardown.
    """
    async with Redis.from_url(redis_url(), decode_responses=True) as r:
        async with r.pubsub() as ps:
            await ps.subscribe(_channel(thread_id))
            while True:
                msg = await ps.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if msg and msg.get("type") == "message":
                    return
