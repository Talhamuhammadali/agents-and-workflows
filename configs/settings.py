"""LLM settings."""

from typing import Any

# Public (API) models
ANTHROPIC_CLAUDE_SONNET_4_6: dict[str, Any] = {
    "model": "claude-sonnet-4-6",
    "temperature": 1,
    "max_tokens": 64000,
    "model_kwargs": {"thinking": {"type": "enabled", "budget_tokens": 10000}},
}

GEMINI_3_1_PRO: dict[str, Any] = {
    "model": "gemini-3.1-pro-preview",
    "temperature": 0.7,
    "thinking_level": "low",
    "include_thoughts": True,
    "streaming": True,
}

OPENAI_GPT_5_4: dict[str, Any] = {
    "model": "gpt-5.4-mini",
    "temperature": 1,
    "reasoning": {"effort": "medium", "summary": "auto"},
    "output_version": "responses/v1",
}

# Enterprise (Vertex AI) models
VERTEX_GEMINI_3_1_PRO: dict[str, Any] = {
    "model": "gemini-3.1-pro-preview",
    "temperature": 0.7,
    "thinking_level": "low",
    "include_thoughts": True,
    "vertexai": True,
    "project": "ekai-dev",
    "location": "global",
}

AZURE_OPENAI_GPT_5_4: dict[str, Any] = {
    "azure_deployment": "gpt-5-4-mini-2",
    "model_name": "gpt-5.4-mini",
    "api_version": "2025-04-01-preview",
    "temperature": 1,
    "reasoning": {"effort": "medium", "summary": "auto"},
    "output_version": "responses/v1",
}

VERTEX_CLAUDE_SONNET_4_6: dict[str, Any] = {
    "model": "claude-sonnet-4-6",
    "temperature": 1,
    "max_tokens": 64000,
    "model_kwargs": {"thinking": {"type": "enabled", "budget_tokens": 10000}},
}
