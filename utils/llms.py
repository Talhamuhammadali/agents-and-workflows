"""All llms providers utils with langchain."""

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
    GEMINI_3_1_PRO,
    OPENAI_GPT_5_4,
    VERTEX_CLAUDE_SONNET_4_6,
    VERTEX_GEMINI_3_1_PRO,
)

load_dotenv()
# Public API models
anthropic_claude_sonnet_4_6 = ChatAnthropic(**ANTHROPIC_CLAUDE_SONNET_4_6)

gemini_3_1_pro = ChatGoogleGenerativeAI(**GEMINI_3_1_PRO)

openai_gpt_5_4 = ChatOpenAI(**OPENAI_GPT_5_4)

# Enterprise (Azure) models
azure_openai_gpt_5_4 = AzureChatOpenAI(**AZURE_OPENAI_GPT_5_4)

# Enterprise (Vertex AI) models
vertex_gemini_3_1_pro = ChatGoogleGenerativeAI(**VERTEX_GEMINI_3_1_PRO)

vertex_claude_sonnet_4_6 = ChatAnthropicVertex(
    **VERTEX_CLAUDE_SONNET_4_6,
    project="ekai-dev",
    location="us-east5",
)


def test_llm(name: str, llm: BaseChatModel) -> None:
    """Send a simple test message to an LLM and print the response."""
    print(f"\n{'=' * 50}")
    print(f"Testing: {name}")
    print(f"{'=' * 50}")
    try:
        ai_message = None
        for chunk in llm.stream("Think of something interesting to say. then say it in creative 2-3 sentences"):
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
    except Exception as e:
        print(f"Error: {e}")


# use uv run python -m utils.llms > utils/response_blocks.txt
if __name__ == "__main__":
    models = {
        "Anthropic Claude Sonnet 4.6": anthropic_claude_sonnet_4_6,
        "Gemini 3.1 Pro": gemini_3_1_pro,
        "OpenAI GPT-5.4": openai_gpt_5_4,
        "Azure OpenAI GPT-5.4": azure_openai_gpt_5_4,
        "Vertex Gemini 3.1 Pro": vertex_gemini_3_1_pro,
        "Vertex Claude Sonnet 4.6": vertex_claude_sonnet_4_6,
    }

    for name, llm in models.items():
        test_llm(name, llm)
