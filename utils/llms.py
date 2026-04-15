"""All llms providers utils with langchain."""

from enum import StrEnum
from pprint import pprint
from typing import Any

from dotenv import load_dotenv
from langchain.chat_models import BaseChatModel
from langchain_anthropic import ChatAnthropic
from langchain_google_genai.chat_models import ChatGoogleGenerativeAI
from langchain_google_vertexai.model_garden import ChatAnthropicVertex
from langchain_openai import AzureChatOpenAI, ChatOpenAI

from configs.settings import (
    ANTHROPIC_CLAUDE_SONNET_4_6,
    AZURE_OPENAI_GPT_5_4,
    GEMINI_2_5_PRO,
    GEMINI_3_1_PRO,
    OPENAI_GPT_5_4,
    VERTEX_CLAUDE_SONNET_4_6,
    VERTEX_GEMINI_2_5_PRO,
    VERTEX_GEMINI_3_1_PRO,
)

load_dotenv()
# Public API models
anthropic_claude_sonnet_4_6 = ChatAnthropic(**ANTHROPIC_CLAUDE_SONNET_4_6)

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
    location="us-east5",
)


class Model(StrEnum):
    """Avaialble models for testing."""

    CLAUDE = "claude"
    GEMINI_2_5 = "gemini-2.5"
    GPT = "gpt"
    AZURE_GPT = "azure-gpt"
    VERTEX_GEMINI = "vertex-gemini"
    VERTEX_GEMINI_2_5 = "vertex-gemini-2.5"
    VERTEX_CLAUDE = "vertex-claude"


MODELS: dict[Model, BaseChatModel] = {
    Model.CLAUDE: anthropic_claude_sonnet_4_6,
    Model.GEMINI_2_5: gemini_2_5_pro,
    Model.GPT: openai_gpt_5_4,
    Model.AZURE_GPT: azure_openai_gpt_5_4,
    Model.VERTEX_GEMINI: vertex_gemini_3_1_pro,
    Model.VERTEX_GEMINI_2_5: vertex_gemini_2_5_pro,
    Model.VERTEX_CLAUDE: vertex_claude_sonnet_4_6,
}


def test_llm(name: str, llm: BaseChatModel) -> None:
    """Send a simple test message to an LLM and print the response."""
    print(f"\n{'=' * 50}")
    print(f"Testing: {name}")
    print(f"{'=' * 50}")
    try:
        ai_message = None
        for chunk in llm.stream("Think ultra of something interesting to say. then say it in creative 2-3 sentences"):
            # pprint(chunk, indent=2)
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
    except Exception as e:
        print(f"Error: {e}")


# use uv run python -m utils.llms > utils/response_blocks.txt
if __name__ == "__main__":
    for name, llm in MODELS.items():
        test_llm(name, llm)
