"""FastAPI backend serving dummy agent conversation data.

Each thread stores a flat MessageResponse[] list. The UI accumulator folds
it into the rendered shape (see ui/docs/sse-streaming.md).
"""

import asyncio
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from ui.backend.models import MessageResponse, StreamRequest
from ui.backend.dummy import THREADS, _msg, _now

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# --- Routes --------------------------------------------------------------

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


def _chunks(text: str, n: int = 4) -> list[str]:
    """Split text into ~n pieces so streaming feels live."""
    if not text:
        return [""]
    size = max(1, len(text) // n)
    return [text[i : i + size] for i in range(0, len(text), size)]


DEMO_TOOLS = [
    (
        "read_file",
        {"path": "notes.txt"},
        "Some existing notes.\n- item 1\n- item 2\n",
    ),
    (
        "write_file",
        {
            "path": "demo.md",
            "content": "# Demo\n\nWritten by the dummy agent to exercise every renderer.\n",
        },
        "File written: demo.md (72 bytes)",
    ),
    (
        "edit_file",
        {
            "path": "demo.md",
            "old_string": "Written by the dummy agent to exercise every renderer.",
            "new_string": "Edited by the dummy agent — diff view should show this swap.",
        },
        "File edited: demo.md",
    ),
    (
        "bash",
        {"command": "pytest tests/ -v"},
        "===== test session starts =====\n"
        "collected 8 items\n\n"
        "tests/test_parse.py::test_basic PASSED\n"
        "tests/test_parse.py::test_empty PASSED\n"
        "tests/test_parse.py::test_unicode PASSED\n"
        "tests/test_io.py::test_read PASSED\n"
        "tests/test_io.py::test_write PASSED\n"
        "tests/test_cli.py::test_help PASSED\n"
        "tests/test_render.py::test_basic PASSED\n"
        "tests/test_render.py::test_streaming PASSED\n\n"
        "===== 8 passed in 1.24s =====\n",
    ),
    (
        "update_todos",
        {
            "todos": [
                {"id": "d1", "task": "Kick the tires on every tool", "completed": True},
                {"id": "d2", "task": "Confirm the fallback renderer fires", "completed": True},
                {"id": "d3", "task": "Wire in the real agent", "completed": False},
            ],
        },
        "Todos updated. 3 item(s) in list.",
    ),
    (
        # Unknown tool — exercises FallbackView.
        "fetch_url",
        {"url": "https://example.com/quantum-refs", "format": "markdown"},
        "Fetched 2KB of markdown from example.com/quantum-refs",
    ),
]


_EXT_TO_LANG = {
    ".md": "markdown",
    ".py": "python",
    ".txt": "plaintext",
    ".json": "json",
    ".js": "javascript",
}


def _lang_for(path: str) -> str:
    for ext, lang in _EXT_TO_LANG.items():
        if path.endswith(ext):
            return lang
    return "plaintext"


def _apply_tool_side_effect(thread: dict, name: str, args: dict) -> None:
    """Mutate thread state as if the tool actually ran.

    Makes the /state re-fetch after a stream visibly change the sidebar,
    artifact panel, and todos — confirming the split endpoint wiring.
    """
    if name == "write_file":
        path = args["path"]
        if not any(f["name"] == path for f in thread["workspace"]):
            thread["workspace"].append({"name": path, "type": "file"})
        thread["artifact"] = {
            "title": path,
            "language": _lang_for(path),
            "content": args["content"],
        }
    elif name == "edit_file":
        art = thread.get("artifact")
        if art and art["title"] == args["path"]:
            thread["artifact"] = {
                **art,
                "content": art["content"].replace(args["old_string"], args["new_string"]),
            }
    elif name == "update_todos":
        thread["todos"] = list(args["todos"])


async def _dummy_reply(thread_id: str, user_message: str):
    """Emit a canned AI turn that exercises every tool renderer."""
    thread = THREADS[thread_id]
    ai_id = f"ai-{uuid.uuid4().hex[:6]}"

    def mk(mtype, content):
        return _msg(
            ai_id, "ai", mtype, content,
            thread_id=thread_id, name="dummy-agent", timestamp=_now(),
        )

    reasoning = mk(
        "reasoning",
        f"User said: \"{user_message[:80]}\".\n\n"
        "I'll walk through every tool I have so each renderer lights up:\n"
        "1. read_file  — path-only view\n"
        "2. write_file — show the written content\n"
        "3. edit_file  — old→new diff\n"
        "4. bash       — command + output (streamed)\n"
        "5. update_todos — mini checklist\n"
        "6. fetch_url  — unknown tool, falls through to the JSON view",
    )
    for chunk in _chunks(reasoning.content, n=8):
        yield reasoning.model_copy(update={"content": chunk})
        await asyncio.sleep(0.28)

    intro = mk("text", "Demoing every tool in one turn — watch the renderers.")
    for chunk in _chunks(intro.content, n=6):
        yield intro.model_copy(update={"content": chunk})
        await asyncio.sleep(0.25)

    for name, args, result in DEMO_TOOLS:
        call_id = f"call_{uuid.uuid4().hex[:6]}"
        yield mk("tool_call", {"id": call_id, "name": name, "type": "tool_call", "args": args})
        _apply_tool_side_effect(thread, name, args)
        await asyncio.sleep(0.5)

        if name == "bash":
            # Stream bash output line-by-line to exercise tool_result chunking.
            for line in result.splitlines(keepends=True):
                yield _msg(
                    call_id, "tool_result", "tool_result", line,
                    thread_id=thread_id, name=name, timestamp=_now(),
                )
                await asyncio.sleep(0.2)
        else:
            yield _msg(
                call_id, "tool_result", "tool_result", result,
                thread_id=thread_id, name=name, timestamp=_now(),
            )
            await asyncio.sleep(0.45)

    closing = mk(
        "text",
        "Done — every renderer got a turn. Expand any tool call above to inspect it.",
    )
    for chunk in _chunks(closing.content, n=6):
        yield closing.model_copy(update={"content": chunk})
        await asyncio.sleep(0.25)


@app.post("/api/threads/{thread_id}/stream")
async def stream_reply(thread_id: str, body: StreamRequest):
    if thread_id not in THREADS:
        raise HTTPException(404, "Thread not found")

    thread = THREADS[thread_id]
    user_msg = _msg(
        f"h-{uuid.uuid4().hex[:6]}", "human", "text", body.message,
        thread_id=thread_id, timestamp=_now(),
    )

    async def gen():
        emitted: list[MessageResponse] = [user_msg]
        yield user_msg.model_dump_json() + "\n"
        async for ev in _dummy_reply(thread_id, body.message):
            emitted.append(ev)
            yield ev.model_dump_json() + "\n"
        thread["messages"].extend(emitted)
        thread["updated_at"] = _now()

    return StreamingResponse(gen(), media_type="application/x-ndjson")
