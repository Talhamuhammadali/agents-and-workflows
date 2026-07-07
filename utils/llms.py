"""All llms providers utils with langchain."""

from enum import StrEnum
from pprint import pprint
from typing import Any

from dotenv import load_dotenv
from langchain.chat_models import BaseChatModel
from langchain_anthropic import ChatAnthropic
from langchain_core.callbacks.usage import UsageMetadataCallbackHandler
from langchain_core.runnables import RunnableConfig
from langchain_google_genai.chat_models import ChatGoogleGenerativeAI
from langchain_google_vertexai.model_garden import ChatAnthropicVertex
from langchain_openai import AzureChatOpenAI, ChatOpenAI

from configs.settings import (
    ANTHROPIC_CLAUDE_FABLE_5,
    ANTHROPIC_CLAUDE_OPUS_4_7,
    ANTHROPIC_CLAUDE_SONNET_4_6,
    ANTHROPIC_CLAUDE_SONNET_5,
    AZURE_OPENAI_GPT_5_4,
    GEMINI_2_5_PRO,
    GEMINI_3_1_PRO,
    OPENAI_GPT_5_4,
    VERTEX_CLAUDE_FABLE_5,
    VERTEX_CLAUDE_OPUS_4_7,
    VERTEX_CLAUDE_SONNET_4_6,
    VERTEX_CLAUDE_SONNET_5,
    VERTEX_GEMINI_2_5_PRO,
    VERTEX_GEMINI_3_1_PRO,
)
from utils.snowflake import get_cortext_claude_sonnet_4_5

load_dotenv()
# Public API models
anthropic_claude_sonnet_4_6 = ChatAnthropic(**ANTHROPIC_CLAUDE_SONNET_4_6)
anthropic_claude_opus_4_7 = ChatAnthropic(**ANTHROPIC_CLAUDE_OPUS_4_7)
anthropic_claude_sonnet_5 = ChatAnthropic(**ANTHROPIC_CLAUDE_SONNET_5)
anthropic_claude_fable_5 = ChatAnthropic(**ANTHROPIC_CLAUDE_FABLE_5)
gemini_3_1_pro = ChatGoogleGenerativeAI(**GEMINI_3_1_PRO)
gemini_2_5_pro = ChatGoogleGenerativeAI(**GEMINI_2_5_PRO)
openai_gpt_5_4 = ChatOpenAI(**OPENAI_GPT_5_4)

# Enterprise (Azure) models
azure_openai_gpt_5_4 = AzureChatOpenAI(**AZURE_OPENAI_GPT_5_4)

# Enterprise (Vertex AI) models
vertex_gemini_3_1_pro = ChatGoogleGenerativeAI(**VERTEX_GEMINI_3_1_PRO)
vertex_gemini_2_5_pro = ChatGoogleGenerativeAI(**VERTEX_GEMINI_2_5_PRO)
vertex_claude_sonnet_4_6 = ChatAnthropicVertex(
    **VERTEX_CLAUDE_SONNET_4_6,
    project="ekai-dev",
    location="global",
)
vertex_claude_opus_4_7 = ChatAnthropicVertex(
    **VERTEX_CLAUDE_OPUS_4_7,
    project="ekai-dev",
    location="global",
)

vertex_claude_sonnet_5 = ChatAnthropicVertex(
    **VERTEX_CLAUDE_SONNET_5,
    project="ekai-dev",
    location="global",
)

vertex_claude_fable_5 = ChatAnthropicVertex(
    **VERTEX_CLAUDE_FABLE_5,
    project="ekai-dev",
    location="global",
)
# Cortex models
cortext_claude_sonnet_4_5 = get_cortext_claude_sonnet_4_5()


class Model(StrEnum):
    """Avaialble models for testing."""

    CLAUDE = "claude"
    CLAUDE_OPUS_4_7 = "claude-opus-4-7"
    CLAUDE_SONNET_5 = "claude-sonnet-5"
    CLAUDE_FABLE_5 = "claude-fable-5"
    GEMINI_2_5 = "gemini-2.5"
    GEMINI = "gemini"
    GPT = "gpt"
    AZURE_GPT = "azure-gpt"
    VERTEX_GEMINI = "vertex-gemini"
    VERTEX_GEMINI_2_5 = "vertex-gemini-2.5"
    VERTEX_CLAUDE = "vertex-claude"
    CORTEXT_CLAUDE_SONNET_4_5 = "cortext-claude-sonnet-4-5"
    VERTEX_CLAUDE_OPUS_4_7 = "vertex-claude-opus-4-7"
    VERTEX_CLAUDE_SONNET_5 = "vertex-claude-sonnet-5"
    VERTEX_CLAUDE_FABLE_5 = "vertex-claude-fable-5"


MODELS: dict[Model, BaseChatModel] = {
    Model.CLAUDE: anthropic_claude_sonnet_4_6,
    Model.CLAUDE_OPUS_4_7: anthropic_claude_opus_4_7,
    Model.CLAUDE_SONNET_5: anthropic_claude_sonnet_5,
    Model.CLAUDE_FABLE_5: anthropic_claude_fable_5,
    Model.GEMINI: gemini_3_1_pro,
    Model.GEMINI_2_5: gemini_2_5_pro,
    Model.GPT: openai_gpt_5_4,
    Model.AZURE_GPT: azure_openai_gpt_5_4,
    Model.VERTEX_GEMINI: vertex_gemini_3_1_pro,
    Model.VERTEX_GEMINI_2_5: vertex_gemini_2_5_pro,
    Model.VERTEX_CLAUDE: vertex_claude_sonnet_4_6,
    Model.VERTEX_CLAUDE_OPUS_4_7: vertex_claude_opus_4_7,
    Model.VERTEX_CLAUDE_SONNET_5: vertex_claude_sonnet_5,
    Model.VERTEX_CLAUDE_FABLE_5: vertex_claude_fable_5,
    Model.CORTEXT_CLAUDE_SONNET_4_5: cortext_claude_sonnet_4_5,
}


def test_llm(name: str, llm: BaseChatModel) -> None:
    """Send a simple test message to an LLM and print the response."""
    print(f"\n{'=' * 50}")
    print(f"Testing: {name}")
    print(f"{'=' * 50}")
    try:
        ai_message = None
        for chunk in llm.stream(
            # "Ultra think of an in depth fastapi main file. It will support in detail endpoints to manage a library.",
            "Ultra think make a joke",
            config=RunnableConfig(callbacks=[UsageMetadataCallbackHandler()]),
        ):
            pprint(chunk, indent=2)
            ai_message = chunk if ai_message is None else ai_message + chunk

        block_types = []
        if ai_message is None:
            return
        for block in ai_message.content_blocks:
            pprint(block, indent=2)
            block_dict = dict(block)
            print(f"  type: {block_dict.get('type')}, keys: {list(block_dict.keys())}")
            if block_dict.get("type") == "non_standard":
                raw_value = block_dict.get("value", {})
                value: dict[str, Any] = raw_value if isinstance(raw_value, dict) else {}
                block_type = value.get("type", [])
            else:
                block_type = block_dict.get("type")
            block_types.append(block_type)
        print(f"Block types in response: {block_types}")
        print(f"Full response usage metadata: {ai_message.usage_metadata}")
        # print("Full ai message: \n\n")
        # pprint(ai_message.model_dump(), indent=2)
    except Exception as e:
        print(f"Error: {e}")


# use uv run python -m utils.llms > utils/response_blocks.txt
if __name__ == "__main__":
    # All llms list
    ALL_LLMS = [model for model in Model]

    # test subset of llms
    TEST_LLMS = [
        Model.VERTEX_CLAUDE_SONNET_5,
        Model.CLAUDE_SONNET_5,
        Model.VERTEX_CLAUDE_FABLE_5,
        Model.CLAUDE_FABLE_5,
    ]
    test_pairs = [(name.value, MODELS[name]) for name in TEST_LLMS]
    for name, llm in test_pairs:
        test_llm(name, llm)
