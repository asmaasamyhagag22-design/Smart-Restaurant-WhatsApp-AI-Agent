"""Abstract base classes + small value models for every external capability.

Concrete implementations live in sibling modules (``llm_mock.py``,
``llm_anthropic.py``, ``vector_memory.py`` …) and are wired in :mod:`app.deps`.
Keeping the contracts here lets the whole codebase depend on stable interfaces.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.domain import PaymentLink
from app.schemas.entities import CustomerRecord
from app.schemas.enums import PaymentStatus
from app.schemas.messaging import InboundMessage, OutboundMessage


# ── LLM ───────────────────────────────────────────────────────────────
class LLMToolCall(BaseModel):
    id: str = ""
    name: str
    args: dict[str, Any] = Field(default_factory=dict)


class LLMResult(BaseModel):
    text: str = ""
    tool_calls: list[LLMToolCall] = Field(default_factory=list)
    stop_reason: str = ""
    usage: dict[str, Any] = Field(default_factory=dict)


class BaseLLM(ABC):
    """Anthropic-style chat completion with optional tool use."""

    @abstractmethod
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
        """Return the model's reply (text and/or tool calls).

        ``messages`` use Anthropic content shape: ``{"role": ..., "content": str
        | list[block]}``. ``tools`` use the Anthropic tool schema
        (``{"name","description","input_schema"}``).
        """

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
        """Force a JSON object matching ``schema`` via a single tool call."""
        tool = {"name": "emit", "description": "Return the structured result.", "input_schema": schema}
        res = await self.complete(
            system=system,
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            tools=[tool],
            tool_choice={"type": "tool", "name": "emit"},
        )
        return res.tool_calls[0].args if res.tool_calls else {}


# ── Embeddings ────────────────────────────────────────────────────────
class BaseEmbedder(ABC):
    dim: int = 384

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        ...

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed(t) for t in texts]


# ── Vector store ──────────────────────────────────────────────────────
class VectorRecord(BaseModel):
    id: str
    values: list[float]
    metadata: dict[str, Any] = Field(default_factory=dict)


class VectorHit(BaseModel):
    id: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class BaseVectorStore(ABC):
    @abstractmethod
    async def upsert(self, namespace: str, records: list[VectorRecord]) -> None:
        ...

    @abstractmethod
    async def query(
        self,
        namespace: str,
        vector: list[float],
        top_k: int = 5,
        flt: dict[str, Any] | None = None,
    ) -> list[VectorHit]:
        ...

    @abstractmethod
    async def delete(self, namespace: str, ids: list[str] | None = None) -> None:
        ...


# ── Channel (WhatsApp / local simulator) ──────────────────────────────
class BaseChannel(ABC):
    name: str = "base"

    @abstractmethod
    async def send(self, msg: OutboundMessage) -> None:
        """Deliver an outbound message to the user."""

    @abstractmethod
    def parse_inbound(self, payload: dict[str, Any], tenant_id: str) -> list[InboundMessage]:
        """Translate a raw webhook payload into normalized inbound messages."""

    def verify_signature(self, headers: dict[str, str], raw_body: bytes) -> bool:
        """Verify webhook authenticity. Local channel returns True."""
        return True

    async def download_media(self, media_id: str) -> bytes:
        raise NotImplementedError


# ── Payment service provider ──────────────────────────────────────────
class BasePSP(ABC):
    name: str = "base"

    @abstractmethod
    async def create_payment_link(
        self,
        *,
        amount_cents: int,
        reference: str,
        customer: CustomerRecord,
        return_url: str,
        description: str = "",
    ) -> PaymentLink:
        ...

    def verify_webhook(self, headers: dict[str, str], raw_body: bytes) -> bool:
        return True

    @abstractmethod
    def parse_webhook(self, payload: dict[str, Any]) -> tuple[str, PaymentStatus]:
        """Return ``(payment_reference, status)`` from a PSP callback."""


# ── Speech-to-text ────────────────────────────────────────────────────
class BaseSTT(ABC):
    @abstractmethod
    async def transcribe(self, audio: bytes, lang_hint: str = "ar") -> str:
        ...


# ── Vision ────────────────────────────────────────────────────────────
class BaseVision(ABC):
    @abstractmethod
    async def extract_menu(self, image: bytes, prompt: str = "") -> list[dict[str, Any]]:
        """Extract candidate menu items (name/price) from an image."""
