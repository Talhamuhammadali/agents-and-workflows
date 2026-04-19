"""FastAPI routes for the react agent UI.

Helpers live in siblings:
- `ui.backend.stream`        — chunk/message conversion + SSE generator.
- `ui.backend.thread_store`  — Redis thread registry + checkpointer state loading.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from ui.backend.models import CreateThreadRequest, StreamRequest, ThreadMeta
from ui.backend.stream import messages_to_events, sse_event_stream
from ui.backend.thread_store import (
    create_thread,
    delete_thread,
    list_threads,
    load_agent_state,
)
from ui.backend.workspace import list_workspace

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/api/threads")
async def get_threads() -> list[ThreadMeta]:
    return await list_threads()


@app.post("/api/threads")
async def post_thread(body: CreateThreadRequest) -> ThreadMeta:
    return await create_thread(body.title)


@app.delete("/api/threads/{thread_id}")
async def remove_thread(thread_id: str) -> dict:
    await delete_thread(thread_id)
    return {"thread_id": thread_id, "deleted": True}


@app.get("/api/threads/{thread_id}")
async def get_thread(thread_id: str) -> dict:
    """Load persisted messages for a thread and return them as MessageResponse[]."""
    state = await load_agent_state(thread_id)
    events = messages_to_events(state.get("messages", []), thread_id)
    return {
        "thread_id": thread_id,
        "title": "Chat",
        "updated_at": None,
        "messages": [e.model_dump() for e in events],
    }


@app.get("/api/threads/{thread_id}/state")
async def get_thread_state(thread_id: str) -> dict:
    """Panel state — todos + workspace files, both sourced from agent state."""
    state = await load_agent_state(thread_id)
    return {
        "thread_id": thread_id,
        "todos": state.get("todos", []),
        "workspace": await list_workspace(state.get("workspace")),
        "artifact": None,
    }


@app.post("/api/threads/{thread_id}/stream")
async def stream_reply(thread_id: str, body: StreamRequest) -> StreamingResponse:
    """Stream an agent's response as SSE MessageResponse events."""
    if not thread_id:
        raise HTTPException(404, "Thread id not provided.")
    if not body.message:
        raise HTTPException(400, "Message not provided.")

    return StreamingResponse(
        sse_event_stream(thread_id, body.message),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "connection": "keep-alive"},
    )
