"""LLM settings."""

# Public (API) models
ANTHROPIC_CLAUDE_SONNET_4_6 = {
    "model": "claude-sonnet-4-6",
    "temperature": 1,
    "max_tokens": 64000,
    "model_kwargs": {
        "thinking": {"type": "adaptive"}
    },
}

GEMINI_3_1_PRO = {
    "model": "gemini-3.1-pro-preview",
    "temperature": 0.7,
    "thinking_level": "low",
    "include_thoughts": True,
}

OPENAI_GPT_5_4 = {
    "model": "gpt-5.4",
    "temperature": 1,
}

# Enterprise (Vertex AI) models
VERTEX_CLAUDE_SONNET_4_6 = {
    "model": "claude-sonnet-4-6",
    "temperature": 1,
    "max_tokens": 64000,
    "model_kwargs": {
        "thinking": {"type": "adaptive"}
    },
}
