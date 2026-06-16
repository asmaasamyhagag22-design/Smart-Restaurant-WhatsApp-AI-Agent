"""Google Gemini provider (via the unified google-genai SDK).

Works two ways, auto-selected from settings:
- **Vertex AI**: set ``GCP_PROJECT`` (+ ``VERTEX_REGION``) — auth via Application
  Default Credentials, no key. (`pip install "google-genai"`.)
- **Gemini Developer API**: set ``GOOGLE_API_KEY`` — simplest, no GCP project.

Structured output uses Gemini JSON mode (``response_schema``); free text uses a
plain ``generate_content`` call. Model ids must be ``gemini-*``; a Claude-style
id is replaced with a sane Gemini default so a mis-set env never hard-fails.
"""
from __future__ import annotations

import json
from typing import Any

from app.config import settings
from app.providers.base import BaseLLM, LLMResult

_DEFAULT_MODEL = "gemini-2.5-flash"


def _norm_model(model: str) -> str:
    return model if model and "gemini" in model else _DEFAULT_MODEL


class GeminiLLM(BaseLLM):
    def __init__(self) -> None:
        from google import genai

        if settings.gcp_project:
            self._client = genai.Client(
                vertexai=True, project=settings.gcp_project, location=settings.vertex_region
            )
        elif settings.google_api_key:
            self._client = genai.Client(api_key=settings.google_api_key)
        else:
            raise RuntimeError("Gemini needs GCP_PROJECT (Vertex) or GOOGLE_API_KEY")

    def _contents(self, messages: list[dict[str, Any]]) -> list:
        from google.genai import types

        out = []
        for m in messages:
            role = "model" if m.get("role") == "assistant" else "user"
            content = m.get("content", "")
            if isinstance(content, str):
                text = content
            else:  # content blocks (we only forward text parts here)
                text = " ".join(
                    b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"
                )
            out.append(types.Content(role=role, parts=[types.Part.from_text(text=text)]))
        return out

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
        from google.genai import types

        cfg = types.GenerateContentConfig(
            system_instruction=system or None,
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        resp = await self._client.aio.models.generate_content(
            model=_norm_model(model), contents=self._contents(messages), config=cfg
        )
        return LLMResult(text=resp.text or "")

    async def structured(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        model: str,
        schema: dict[str, Any],
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        from google.genai import types

        cfg = types.GenerateContentConfig(
            system_instruction=system or None,
            temperature=temperature,
            max_output_tokens=max_tokens,
            response_mime_type="application/json",
            response_schema=schema,
        )
        resp = await self._client.aio.models.generate_content(
            model=_norm_model(model), contents=self._contents(messages), config=cfg
        )
        try:
            return json.loads(resp.text)
        except Exception:
            return {}
