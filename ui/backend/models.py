"""Models for the UI backend."""

from enum import Enum

from pydantic import BaseModel
from typing import Dict, List, Literal, Optional, Union


class MessageTypes(str, Enum):
    """Message types for streaming LLM responses and history api."""
    REASONING = "reasoning"
    TEXT = "text"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    NOTIFICATION = "notification"
    

class MessageResponse(BaseModel):
    """Model for messages sent from the backend to the frontend."""
    id: str                              # merge key — same id extends same block
    thread_id: Optional[str]              # for threading messages in the UI, if needed
    checkpoint_id: Optional[str]
    message_type: MessageTypes           # reasoning | text | tool_call | ...
    role_type: Literal["ai", "human", "tool_result"]
    subtype: Optional[str]               # artifact type, when role produces one
    content: Union[str, Dict, List]      # payload — shape depends on message_type
    name: Optional[str]
    timestamp: str


class StreamRequest(BaseModel):
    """Body for POST /api/threads/{thread_id}/stream."""
    message: str