"""Deterministic mock LLM — lets the whole agent run locally with no API key.

Nodes tag their system prompt with a machine-readable first line, e.g.
``[task:intent]``. The mock branches on that tag; the real Anthropic provider
simply treats it as ordinary text, so nodes are identical for both.
"""
from __future__ import annotations

import re
from typing import Any

from app.providers.base import BaseLLM, LLMResult, LLMToolCall
from app.services.text import detect_lang, guess_intent

_TASK_RE = re.compile(r"\[task:([a-z_]+)\]")


def _task(system: str) -> str:
    m = _TASK_RE.search(system or "")
    return m.group(1) if m else ""


def _last_user_text(messages: list[dict[str, Any]]) -> str:
    for msg in reversed(messages):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, str):
                return content
            # content blocks
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    return block.get("text", "")
    return ""


class MockLLM(BaseLLM):
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
        task = _task(system)
        user = _last_user_text(messages)
        if tools and tool_choice:
            name = tool_choice.get("name", "emit") if isinstance(tool_choice, dict) else "emit"
            return LLMResult(
                tool_calls=[LLMToolCall(id="mock", name=name, args=self._emit(task, user))],
                stop_reason="tool_use",
            )
        return LLMResult(text=self._freetext(task, user))

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
        return self._emit(_task(system), _last_user_text(messages))

    # ── deterministic behaviours ──────────────────────────────────────
    def _emit(self, task: str, user: str) -> dict[str, Any]:
        if task == "intent":
            return {"intent": guess_intent(user).value, "lang": detect_lang(user).value}
        if task == "reflect":
            return {"needs_replan": False, "reason": "deterministic policy handles flow"}
        return {}

    def _freetext(self, task: str, user: str) -> str:
        lang = detect_lang(user)
        if lang.value == "ar-EG":
            return "أهلاً بيك في مطعمنا 👋 تحب تطلب إيه النهاردة؟ تقدر تقولي اسم الأكل اللي نفسك فيه."
        return "Welcome 👋 What would you like to order today? Tell me what you're craving."
