"""Helpers for building MessageResponse events from LangChain content.

Private to `ui.backend.stream` — shared by the streaming and rehydration paths.
"""

from datetime import UTC, datetime
from typing import Any

from ui.backend.models import MessageResponse, MessageTypes


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def as_text(content: Any) -> str:
    """Flatten message content (str or list of parts) to a plain string."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            (p.get("text") or p.get("thinking") or "") if isinstance(p, dict) else str(p)
            for p in content
        )
    return str(content)


def ai_content_events(
    content: Any,
    tool_calls: list[dict] | None,
    thread_id: str,
    parent_run_id: str,
    ts: str,
    name: str | None,
) -> list[MessageResponse]:
    """Emit reasoning/text/tool_call events from one AI message (or chunk)."""
    events: list[MessageResponse] = []

    if isinstance(content, str) and content:
        events.append(
            MessageResponse(
                id=parent_run_id, thread_id=thread_id, checkpoint_id=None,
                message_type=MessageTypes.TEXT, role_type="ai", subtype=None,
                content=content, name=name, timestamp=ts,
            )
        )
    elif isinstance(content, list):
        for part in content:
            if not isinstance(part, dict):
                continue
            ptype = part.get("type")
            if ptype == "thinking" and part.get("thinking"):
                events.append(
                    MessageResponse(
                        id=parent_run_id, thread_id=thread_id, checkpoint_id=None,
                        message_type=MessageTypes.REASONING, role_type="ai", subtype=None,
                        content=part["thinking"], name=name, timestamp=ts,
                    )
                )
            elif ptype == "text" and part.get("text"):
                events.append(
                    MessageResponse(
                        id=parent_run_id, thread_id=thread_id, checkpoint_id=None,
                        message_type=MessageTypes.TEXT, role_type="ai", subtype=None,
                        content=part["text"], name=name, timestamp=ts,
                    )
                )
            # 'reasoning' parts from Gemini are empty signature carriers — skip.

    for tc in tool_calls or []:
        events.append(
            MessageResponse(
                id=parent_run_id, thread_id=thread_id, checkpoint_id=None,
                message_type=MessageTypes.TOOL_CALL, role_type="ai", subtype=None,
                content={"id": tc.get("id", ""), "name": tc.get("name", ""), "args": tc.get("args", {})},
                name=name, timestamp=ts,
            )
        )

    return events


def tool_result_event(
    content: str, tool_call_id: str, thread_id: str, ts: str, name: str | None
) -> MessageResponse:
    return MessageResponse(
        id=tool_call_id, thread_id=thread_id, checkpoint_id=None,
        message_type=MessageTypes.TOOL_RESULT, role_type="tool_result", subtype=None,
        content=content, name=name, timestamp=ts,
    )
