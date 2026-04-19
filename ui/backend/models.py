"""Models for the UI backend."""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel


class MessageTypes(StrEnum):
    """Message types for streaming LLM responses and history api."""

    REASONING = "reasoning"
    TEXT = "text"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    NOTIFICATION = "notification"


class MessageResponse(BaseModel):
    """Model for messages sent from the backend to the frontend."""

    id: str  # merge key — same id extends same block
    thread_id: str | None  # for threading messages in the UI, if needed
    checkpoint_id: str | None
    message_type: MessageTypes  # reasoning | text | tool_call | ...
    role_type: Literal["ai", "human", "tool_result"]
    subtype: str | None  # artifact type, when role produces one
    content: str | dict | list  # payload — shape depends on message_type
    name: str | None
    timestamp: str


class StreamRequest(BaseModel):
    """Body for POST /api/threads/{thread_id}/stream."""

    message: str


class ThreadMeta(BaseModel):
    """Thread registry entry — persisted in Redis under `ui:thread:{thread_id}`."""

    thread_id: str
    title: str
    updated_at: str


class CreateThreadRequest(BaseModel):
    """Body for POST /api/threads — title is optional, defaults to 'New chat'."""

    title: str | None = None
