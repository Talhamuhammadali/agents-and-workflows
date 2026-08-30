"""llms using aws bedrock converse API."""

import os

from langchain_aws import ChatBedrockConverse
from pydantic import SecretStr

from configs.settings import BEDROCK_NEMOTRON_NANO_3_30B


def get_bedrock_nemotron_nano_3_30b() -> ChatBedrockConverse:
    """Nemotron Nano 3 30B via the Bedrock Converse API.

    Converse returns the reasoning trace as a reasoningContent block, which
    langchain-aws maps to a standard reasoning content block. The Mantle
    OpenAI-compatible endpoint also emits the trace, but langchain-openai's
    Chat Completions converters drop it.

    Returns
    -------
    ChatBedrockConverse
        Chat model authenticated with the Bedrock API key, configured from
        BEDROCK_NEMOTRON_NANO_3_30B.
    """
    return ChatBedrockConverse(
        api_key=SecretStr(os.environ["BEDROCK_API_KEY"]),
        **BEDROCK_NEMOTRON_NANO_3_30B,
    )
