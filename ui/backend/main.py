"""FastAPI backend serving dummy agent conversation data.

Each thread stores a flat MessageResponse[] list. The UI accumulator folds
it into the rendered shape (see ui/docs/sse-streaming.md).
"""
import os

from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from ui.backend.models import MessageResponse, StreamRequest

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.redis import AsyncRedisSaver
from langgraph.store.redis import AsyncRedisStore
from agentic_patterns.react_agent.agent import REACT_AGENT_BUILDER
from agentic_patterns.react_agent.state import ReactAgentContextSchema

from ui.backend.dummy import THREADS, _msg 

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/api/threads")
def list_threads():
    return [
        {"thread_id": t["thread_id"], "title": t["title"], "updated_at": t["updated_at"]}
        for t in THREADS.values()
    ]


@app.get("/api/threads/{thread_id}")
def get_thread(thread_id: str):
    """Messages + metadata only. Panel state lives under /state."""
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
def get_thread_state(thread_id: str):
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
async def stream_reply(thread_id: str, body: StreamRequest):
    """Stream an agents response."""
    if not thread_id:
        raise HTTPException(404, "Thread id not provided.")
    if not body.message:
        raise HTTPException(400, "Message not provided.")
    
    redis_url = os.environ.get("REDIS_URL")
    async with AsyncRedisStore.from_conn_string(redis_url) as store:
        store.setup()
        async with AsyncRedisSaver.from_conn_string(redis_url) as ch:
            await ch.asetup()
            print("Setup complete, starting stream...")
            agent = REACT_AGENT_BUILDER.compile(store=store, checkpointer=ch)
            context = ReactAgentContextSchema(
                workspace=Path("tests/workspace/sandbox").resolve(),
                agent_name="ReactAgent",
                model="gemini-2.5-pro",
            )
            
            config = RunnableConfig(
                configurable={"thread_id": thread_id},
            )
            
            inputs = {"message": body.message,}
            
            async def event_generator():
                async for chunk in agent.astream(inputs, context=context, config=config, version="v2"):
                    print(f"Yielding chunk: \n\n{chunk}")
                    yield f"data: {chunk.model_json()}\n\n"
            return StreamingResponse(
                event_generator(),
                media_type="text/event-stream",
                headers={
                     "Cache-Control": "no-cache", "X-Accel-Buffering": "no", "connection": "keep-alive"
                    },
            )