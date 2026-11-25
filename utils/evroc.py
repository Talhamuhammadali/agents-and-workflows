"""llms hosted on the Evroc neo cloud OpenAI-compatible Chat Completions API."""

import os
from typing import Any

from langchain_core.messages import AIMessage, AIMessageChunk
from langchain_core.outputs import ChatGenerationChunk, ChatResult
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from configs.settings import EVROC_GLM_5_3

MODEL_PROVIDER = "evroc"


class ChatEvroc(ChatOpenAI):
    """ChatOpenAI that keeps the reasoning trace Evroc returns.

    Evroc streams the trace as a non-standard reasoning field on each delta
    and on the final message. ChatOpenAI only parses official OpenAI fields, so
    the trace is dropped. This subclass copies it into
    additional_kwargs["reasoning_content"] and tags the message with its own
    model provider. Having no registered block translator, langchain-core
    falls back to best-effort parsing, which turns reasoning_content into a
    standard reasoning content block.
    """

    def _convert_chunk_to_generation_chunk(
        self,
        chunk: dict,
        default_chunk_class: type,
        base_generation_info: dict | None,
    ) -> ChatGenerationChunk | None:
        generation_chunk = super()._convert_chunk_to_generation_chunk(chunk, default_chunk_class, base_generation_info)
        if generation_chunk is None:
            return None
        message = generation_chunk.message
        choices = chunk.get("choices") or []
        delta = (choices[0].get("delta") or {}) if choices else {}
        if isinstance(message, AIMessageChunk):
            if reasoning := delta.get("reasoning"):
                message.additional_kwargs["reasoning_content"] = reasoning
            message.response_metadata["model_provider"] = MODEL_PROVIDER
        return generation_chunk

    def _create_chat_result(
        self,
        response: Any,
        generation_info: dict | None = None,
    ) -> ChatResult:
        result = super()._create_chat_result(response, generation_info)
        response_dict = response if isinstance(response, dict) else response.model_dump()
        for generation, choice in zip(result.generations, response_dict.get("choices") or []):
            message = generation.message
            if isinstance(message, AIMessage):
                if reasoning := (choice.get("message") or {}).get("reasoning"):
                    message.additional_kwargs["reasoning_content"] = reasoning
                message.response_metadata["model_provider"] = MODEL_PROVIDER
        return result


def get_evroc_glm_5_3() -> ChatEvroc:
    """GLM 5.3 on Evroc with its reasoning trace preserved.

    Returns
    -------
    ChatEvroc
        Chat model pointed at the Evroc base URL, derived from EVROC_API_URL by
        stripping the chat completions path, authenticated with EVROC_API_KEY,
        and configured from EVROC_GLM_5_3.
    """
    return ChatEvroc(
        base_url=os.getenv("EVROC_API_URL", "").removesuffix("/chat/completions"),
        api_key=SecretStr(os.getenv("EVROC_API_KEY", "")),
        **EVROC_GLM_5_3,
    )
