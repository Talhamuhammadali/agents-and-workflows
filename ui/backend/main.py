"""FastAPI backend serving dummy agent conversation data.

Each thread stores a flat MessageResponse[] list. The UI accumulator folds
it into the rendered shape (see ui/docs/sse-streaming.md).
"""

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.redis import AsyncRedisSaver
from langgraph.store.redis import AsyncRedisStore

from agentic_patterns.react_agent.agent import REACT_AGENT_BUILDER
from agentic_patterns.react_agent.state import ReactAgentContextSchema
from ui.backend.dummy import THREADS
from ui.backend.models import StreamRequest
from utils.llms import Model

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/api/threads")
def list_threads() -> list[dict]:
    """List threads with metadata only, no messages."""
    return [{"thread_id": t["thread_id"], "title": t["title"], "updated_at": t["updated_at"]} for t in THREADS.values()]


@app.get("/api/threads/{thread_id}")
def get_thread(thread_id: str) -> dict:
    """Load entire thread with messages."""
    if thread_id not in THREADS:
        raise HTTPException(404, "Thread not found")
    t = THREADS[thread_id]
    return {
        "thread_id": t["thread_id"],
        "title": t["title"],
        "updated_at": t["updated_at"],
        "messages": t["messages"],
    }


@app.get("/api/threads/{thread_id}/state")
def get_thread_state(thread_id: str) -> dict:
    """Current todos / workspace / artifact for the thread."""
    if thread_id not in THREADS:
        raise HTTPException(404, "Thread not found")
    t = THREADS[thread_id]
    return {
        "todos": t["todos"],
        "workspace": t["workspace"],
        "artifact": t["artifact"],
    }


@app.post("/api/threads/{thread_id}/stream")
async def stream_reply(thread_id: str, body: StreamRequest) -> StreamingResponse:
    """Stream an agent's response."""
    if not thread_id:
        raise HTTPException(404, "Thread id not provided.")
    if not body.message:
        raise HTTPException(400, "Message not provided.")

    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

    async with AsyncRedisStore.from_conn_string(redis_url) as store:
        await store.setup()
        async with AsyncRedisSaver.from_conn_string(redis_url) as ch:
            await ch.asetup()
            print("Setup complete, starting stream...")
            agent = REACT_AGENT_BUILDER.compile(store=store, checkpointer=ch)
            context = ReactAgentContextSchema(
                workspace=Path("tests/workspaces/sandbox").resolve(),
                agent_name="ReactAgent",
                model=Model.VERTEX_GEMINI_2_5.value,
            )

            config = RunnableConfig(
                configurable={"thread_id": thread_id},
            )

            inputs = {"message": body.message}

            async def event_generator():  # type: ignore[no-untyped-def]
                async for chunk in agent.astream(
                    inputs, context=context, config=config, stream_mode=["custom"], version="v2"
                ):  # type: ignore[call-overload]
                    print(f"Yielding chunk: \n\n{chunk}")
                    yield f"data: {chunk['data'].model_json()}\n\n"

            return StreamingResponse(
                event_generator(),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "connection": "keep-alive"},
            )
