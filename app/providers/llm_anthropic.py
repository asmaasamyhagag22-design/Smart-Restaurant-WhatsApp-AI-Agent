"""Real Claude provider — direct Anthropic API or Google Vertex AI.

Both backends speak the same Messages API, so they share one implementation; only
the client construction (and auth) differs:

- ``AnthropicLLM`` — direct API, auth via ``ANTHROPIC_API_KEY``.
- ``VertexLLM``    — Claude on Vertex, auth via Google Application Default
  Credentials (no API key). Needs ``pip install "anthropic[vertex]"`` and a GCP
  project with the Claude models enabled in Vertex Model Garden.
"""
from __future__ import annotations

from typing import Any

from app.config import settings
from app.providers.base import BaseLLM, LLMResult, LLMToolCall


class _AnthropicCompatLLM(BaseLLM):
    """Shared Messages-API logic for any anthropic-compatible async client."""

    def __init__(self, client: Any) -> None:
        self._client = client

    async def complete(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        model: str,
        max_tokens: int = 1024,
        temperature: float = 0.2,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: dict[str, Any] | None = None,
    ) -> LLMResult:
        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
        if tool_choice:
            kwargs["tool_choice"] = tool_choice

        msg = await self._client.messages.create(**kwargs)

        text = ""
        calls: list[LLMToolCall] = []
        for block in msg.content:
            btype = getattr(block, "type", "")
            if btype == "text":
                text += block.text
            elif btype == "tool_use":
                calls.append(LLMToolCall(id=block.id, name=block.name, args=dict(block.input)))

        usage = getattr(msg, "usage", None)
        return LLMResult(
            text=text,
            tool_calls=calls,
            stop_reason=getattr(msg, "stop_reason", "") or "",
            usage={
                "input_tokens": getattr(usage, "input_tokens", 0),
                "output_tokens": getattr(usage, "output_tokens", 0),
            },
        )


class AnthropicLLM(_AnthropicCompatLLM):
    def __init__(self) -> None:
        from anthropic import AsyncAnthropic

        super().__init__(AsyncAnthropic(api_key=settings.anthropic_api_key))


class VertexLLM(_AnthropicCompatLLM):
    def __init__(self) -> None:
        from anthropic import AsyncAnthropicVertex

        super().__init__(
            AsyncAnthropicVertex(project_id=settings.gcp_project, region=settings.vertex_region)
        )
