"""Subagent-as-tool (LangGraph subgraph mode C) with four checkpointer configs.

The parent always uses AsyncRedisSaver. Modes:

    own_same_thread -> subagent has its own AsyncRedisSaver; the tool wrapper
                       forwards the parent's RunnableConfig directly via
                       ToolRuntime, so the subagent persists under the SAME
                       thread_id as the parent.
    own_new_thread  -> subagent has its own AsyncRedisSaver; the tool wrapper
                       derives a fresh thread_id ("<parent>-fruit" / "-veggie")
                       so each subagent keeps its own thread.
    disabled        -> subagent compiled with checkpointer=False (no persistence).
    default         -> subagent compiled with no checkpointer arg (no persistence).
"""

import asyncio
import os
from typing import Any, Literal

from langchain.agents import create_agent
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool, tool
from langgraph.checkpoint.redis import AsyncRedisSaver
from langgraph.prebuilt import ToolRuntime
from langgraph.store.redis import AsyncRedisStore
from redis.asyncio import Redis

from utils import MODELS, Model

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

Mode = Literal["own_same_thread", "own_new_thread", "disabled", "default"]


async def scan_keys_for_thread(thread_id: str) -> list[str]:
    async with Redis.from_url(REDIS_URL, decode_responses=True) as r:
        return [k async for k in r.scan_iter(match=f"*{thread_id}*")]


async def purge_keys_for_thread(thread_id: str) -> int:
    async with Redis.from_url(REDIS_URL, decode_responses=True) as r:
        keys = [k async for k in r.scan_iter(match=f"*{thread_id}*")]
        if keys:
            await r.delete(*keys)
        return len(keys)


def install_safe_pending_sends_loader() -> None:
    """Make `pending_sends` deserialization tolerate malformed entries.

    langgraph-checkpoint-redis builds pending_sends with a list comprehension,
    so one bad blob raises orjson.JSONDecodeError and aborts the whole snapshot
    load. We replace the comprehension with a per-entry try/except.
    """
    from langgraph.checkpoint.redis.base import BaseRedisSaver, safely_decode

    if getattr(BaseRedisSaver, "_safe_loader_installed", False):
        return

    def _load_checkpoint(self: Any, checkpoint: Any, channel_values: Any, pending_sends: Any) -> Any:
        if not checkpoint:
            return {}
        loaded = checkpoint if isinstance(checkpoint, dict) else __import__("orjson").loads(checkpoint)
        safe_sends: list[Any] = []
        for c, b in pending_sends or []:
            try:
                safe_sends.append(self.serde.loads_typed((safely_decode(c), b)))
            except Exception:
                continue
        return {**loaded, "pending_sends": safe_sends, "channel_values": channel_values}

    BaseRedisSaver._load_checkpoint = _load_checkpoint  # type: ignore[assignment]
    BaseRedisSaver._safe_loader_installed = True  # type: ignore[attr-defined]


async def safe_state_history(parent: Any, config: RunnableConfig) -> tuple[list[Any], list[str]]:
    """Iterate aget_state_history but skip checkpoints whose blobs fail to deserialize.

    Works around a known langgraph-checkpoint-redis bug where one bad pending_sends
    entry aborts the whole iterator with orjson.JSONDecodeError.
    """
    snapshots: list[Any] = []
    skipped: list[str] = []
    it = parent.aget_state_history(config).__aiter__()
    while True:
        try:
            snapshots.append(await it.__anext__())
        except StopAsyncIteration:
            break
        except Exception as e:
            skipped.append(f"{type(e).__name__}: {e}")
    return snapshots, skipped


@tool
def fruit_info(fruit_name: str) -> str:
    """Look up fruit info."""
    return f"Info about {fruit_name}"


@tool
def veggie_info(veggie_name: str) -> str:
    """Look up veggie info."""
    return f"Info about {veggie_name}"


def make_subagents(mode: Mode, sub_saver: AsyncRedisSaver) -> tuple[Any, Any]:
    if mode in ("own_same_thread", "own_new_thread"):
        kw: dict[str, Any] = {"checkpointer": sub_saver}
    elif mode == "disabled":
        kw = {"checkpointer": False}
    else:  # "default"
        kw = {}
    fruit_agent = create_agent(
        model=MODELS[Model.CLAUDE],
        tools=[fruit_info],
        system_prompt="You are a fruit expert. Use the fruit_info tool.",
        **kw,
    )
    veggie_agent = create_agent(
        model=MODELS[Model.CLAUDE],
        tools=[veggie_info],
        system_prompt="You are a veggie expert. Use the veggie_info tool.",
        **kw,
    )
    return fruit_agent, veggie_agent


def _sub_config(runtime: ToolRuntime, mode: Mode, suffix: str) -> RunnableConfig | None:
    if mode == "own_same_thread":
        configurable = runtime.config.get("configurable", {})
        configurable["extra_tacking"] = "some-id"
        return {"configurable": configurable}
    if mode == "own_new_thread":
        parent_thread_id = runtime.config["configurable"]["thread_id"]
        return {"configurable": {"thread_id": f"{parent_thread_id}-{suffix}"}}
    return None


def build_expert_tools(fruit_agent: Any, veggie_agent: Any, mode: Mode) -> list[BaseTool]:
    @tool
    async def ask_fruit_expert(question: str, runtime: ToolRuntime) -> str:
        """Ask the fruit expert."""
        response = await fruit_agent.ainvoke(
            {"messages": [{"role": "user", "content": question}]},
            config=_sub_config(runtime, mode, "fruit"),
        )
        return response["messages"][-1].content

    @tool
    async def ask_veggie_expert(question: str, runtime: ToolRuntime) -> str:
        """Ask the veggie expert."""
        response = await veggie_agent.ainvoke(
            {"messages": [{"role": "user", "content": question}]},
            config=_sub_config(runtime, mode, "veggie"),
        )
        return response["messages"][-1].content

    return [ask_fruit_expert, ask_veggie_expert]


def make_parent(saver: AsyncRedisSaver, store: AsyncRedisStore, expert_tools: list[BaseTool]) -> Any:
    # middleware = [ToolCallLimitMiddleware(tool_name=t.name, run_limit=1) for t in expert_tools]
    return create_agent(
        model=MODELS[Model.CLAUDE],
        tools=expert_tools,
        system_prompt="You are a parent agent. Use the expert tools.",
        checkpointer=saver,
        store=store,
        # middleware=middleware,
    )


async def run_mode(mode: Mode) -> dict[str, Any]:
    parent_thread_id = f"ckpt-mode-{mode}"
    if mode == "own_same_thread":
        sub_thread_ids = [parent_thread_id]
    elif mode == "own_new_thread":
        sub_thread_ids = [f"{parent_thread_id}-fruit", f"{parent_thread_id}-veggie"]
    else:
        sub_thread_ids = []

    purged = await purge_keys_for_thread(parent_thread_id)
    for tid in sub_thread_ids:
        if tid != parent_thread_id:
            purged += await purge_keys_for_thread(tid)
    print(f"  purged {purged} stale redis keys")

    async with (
        AsyncRedisStore.from_conn_string(REDIS_URL) as store,
        AsyncRedisSaver.from_conn_string(REDIS_URL) as saver,
        AsyncRedisSaver.from_conn_string(REDIS_URL) as sub_saver,
    ):
        await store.setup()
        await saver.asetup()
        await sub_saver.asetup()

        fruit_agent, veggie_agent = make_subagents(mode, sub_saver)
        expert_tools = build_expert_tools(fruit_agent, veggie_agent, mode)
        parent = make_parent(saver, store, expert_tools)

        config: RunnableConfig = {"configurable": {"thread_id": parent_thread_id}}
        prompt = "Tell me one fact about apples, then one fact about carrots."
        error: str | None = None
        try:
            await parent.ainvoke(
                {"messages": [{"role": "user", "content": prompt}]},
                config=config,
            )
        except Exception as e:
            error = f"{type(e).__name__}: {e}"

        history, skipped = await safe_state_history(parent, config)
        if skipped and not error:
            error = f"history: skipped {len(skipped)} ({skipped[0]})"

        keys = await scan_keys_for_thread(parent_thread_id)

    return {
        "mode": mode,
        "error": error,
        "parent_ckpts": len(history),
        "skipped_ckpts": len(skipped),
        "redis_key_count": len(keys),
        "redis_keys_sample": sorted(keys)[:6],
    }


install_safe_pending_sends_loader()


async def main() -> None:
    results: list[dict[str, Any]] = []
    for mode in ("own_same_thread", "own_new_thread", "disabled", "default"):
        print(f"\n--- running mode={mode}")
        results.append(await run_mode(mode))

    print(f"\n{'mode':<18} {'parent_ckpts':>13} {'skipped':>8} {'redis_keys':>12}   error")
    print("-" * 90)
    for r in results:
        err = r["error"] or "-"
        print(f"{r['mode']:<18} {r['parent_ckpts']:>13} {r['skipped_ckpts']:>8} {r['redis_key_count']:>12}   {err}")
        for k in r["redis_keys_sample"]:
            print(f"   {k}")


if __name__ == "__main__":
    asyncio.run(main())
