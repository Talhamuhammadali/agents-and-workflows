"""LLM settings."""

from typing import Any

# Public (API) models
ANTHROPIC_CLAUDE_SONNET_4_6: dict[str, Any] = {
    "model": "claude-sonnet-4-6",
    "temperature": 1,
    "max_tokens": 64000,
    "thinking": {"type": "enabled", "budget_tokens": 10000},
    "cache_control": {"type": "ephemeral"},
}

ANTHROPIC_CLAUDE_OPUS_4_7: dict[str, Any] = {
    "model": "claude-opus-4-7",
    "temperature": 1,
    "max_tokens": 64000,
    "thinking": {"type": "adaptive", "display": "summarized"},
    "output_config": {"effort": "xhigh"},
    "cache_control": {"type": "ephemeral"},
}

ANTHROPIC_CLAUDE_SONNET_5: dict[str, Any] = {
    "model": "claude-sonnet-5",
    "max_tokens": 128000,
    "thinking": {"type": "adaptive", "display": "summarized"},
    "output_config": {"effort": "xhigh"},
    "cache_control": {"type": "ephemeral"},
}

ANTHROPIC_CLAUDE_FABLE_5: dict[str, Any] = {
    "model": "claude-fable-5",
    "max_tokens": 128000,
    "thinking": {"type": "adaptive", "display": "summarized"},
    "output_config": {"effort": "xhigh"},
    "cache_control": {"type": "ephemeral"},
}


GEMINI_3_1_PRO: dict[str, Any] = {
    "model": "gemini-3.1-pro-preview",
    "temperature": 0.7,
    "thinking_level": "low",
    "include_thoughts": True,
    "streaming": True,
}
GEMINI_2_5_PRO: dict[str, Any] = {
    "model": "gemini-2.5-pro",
    "temperature": 0.7,
    "include_thoughts": True,
    "thinking_budget": 2056,
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

VERTEX_GEMINI_2_5_PRO: dict[str, Any] = {
    "model": "gemini-2.5-pro",
    "temperature": 0.7,
    "include_thoughts": True,
    "thinking_budget": 2056,
    "streaming": True,
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
    "thinking": {"type": "enabled", "budget_tokens": 10000},
    "cache_control": {"type": "ephemeral"},
}

VERTEX_CLAUDE_OPUS_4_7: dict[str, Any] = {
    "model": "claude-opus-4-7",
    "temperature": 1,
    "max_tokens": 64000,
    "thinking": {"type": "adaptive", "display": "summarized"},
    "output_config": {"effort": "xhigh"},
    "cache_control": {"type": "ephemeral"},
}

VERTEX_CLAUDE_SONNET_5: dict[str, Any] = {
    "model": "claude-sonnet-5",
    "max_tokens": 128000,
    "thinking": {"type": "adaptive", "display": "summarized"},
    "output_config": {"effort": "xhigh"},
    "cache_control": {"type": "ephemeral"},
}

VERTEX_CLAUDE_FABLE_5: dict[str, Any] = {
    "model": "claude-fable-5",
    "max_tokens": 128000,
    "thinking": {"type": "adaptive", "display": "summarized"},
    "output_config": {"effort": "xhigh"},
    "cache_control": {"type": "ephemeral"},
}

# Enterprise (AWS Bedrock) models
BEDROCK_NEMOTRON_NANO_3_30B: dict[str, Any] = {
    "model": "nvidia.nemotron-nano-3-30b",
    "region_name": "us-east-1",
    "temperature": 0.6,
    "top_p": 0.95,
    "max_tokens": 8192,
    # langchain-aws only allowlists known-streaming providers; nvidia isn't one.
    "disable_streaming": False,
    # Takes 'none' | 'low' | 'medium' | 'high'; only 'high' reliably emits a trace.
    "additional_model_request_fields": {"reasoning_effort": "high"},
}

# Cortex models
CORTEXT_CLAUDE_SONNET_4_5: dict[str, Any] = {
    "model": "claude-sonnet-4-6",
    "temperature": 1,
    "max_tokens": 64000,
    "thinking": {"type": "adaptive"},
    "output_config": {"effort": "high"},
    # "cache_control": {"type": "ephemeral"}
}
