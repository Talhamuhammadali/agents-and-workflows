"""Models for the UI backend."""

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel

from utils.llms import Model


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


class PendingInterrupt(BaseModel):
    """A paused interrupt from the agent graph — surfaced for UI Q/A or approval blocks."""

    id: str
    value: Any  # always a list of Question dicts from ask_question today


class AgentStateResponse(BaseModel):
    """Extended state payload — checkpointer values plus any pending interrupts."""

    values: dict
    pending_interrupts: list[PendingInterrupt] = []


class ThreadMeta(BaseModel):
    """Thread registry entry — persisted in Redis under `ui:thread:{thread_id}`."""

    thread_id: str
    title: str
    updated_at: str | None = None


class ThreadHistoryResponse(ThreadMeta):
    """Body for GET /api/threads/{thread_id} — chat history + any paused interrupts."""

    messages: list[MessageResponse] = []
    pending_interrupts: list[PendingInterrupt] = []


class StreamRequest(BaseModel):
    """Body for POST /api/threads/{thread_id}/stream.

    `message` is either a plain str (new user turn) or a dict keyed by interrupt id
    with the answer as the value (resume map for pending interrupts).
    """

    message: str | dict
    model: Model = Model.VERTEX_CLAUDE


class AwsCreds(BaseModel):
    """AWS credentials for the source role, entered per thread in the UI."""

    access_key_id: str
    secret_access_key: str
    region: str
    session_token: str | None = None


class ThreadConfig(BaseModel):
    """Per-thread connection config, set at thread creation and reused each turn.

    The target is either the local minikube (use_local_minikube) or a pasted
    flattened kubeconfig for a remote cluster such as EKS (target_kubeconfig).
    allow_bash unlocks the fileops skill so the agent can validate the CRD with
    kubectl; leave it off for the structured-only surface.
    """

    aws: AwsCreds | None = None
    use_local_minikube: bool = False
    target_kubeconfig: str | None = None
    target_namespace: str = "default"
    allow_bash: bool = False


class CreateThreadRequest(BaseModel):
    """Body for POST /api/threads — title is optional, defaults to 'New chat'."""

    title: str | None = None
    config: ThreadConfig | None = None
