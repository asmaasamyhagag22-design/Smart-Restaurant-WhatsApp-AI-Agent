"""The typed conversation state that flows through the LangGraph nodes.

Each node is a function ``ConvState -> dict`` (a partial update). Side effects
(DB writes, payment links, sends) only happen inside the *tools* node.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.domain import Cart
from app.schemas.enums import Intent, Lang
from app.schemas.messaging import InboundMessage, OutboundMessage


class CustomerCtx(BaseModel):
    """Lightweight customer context loaded at the start of a turn."""

    id: str
    phone: str
    name: str | None = None
    preferred_lang: Lang = Lang.AR
    diet_tags: list[str] = Field(default_factory=list)
    zone: str | None = None
    recent_orders: list[dict[str, Any]] = Field(default_factory=list)


class Turn(BaseModel):
    role: Literal["user", "assistant", "system", "tool"]
    content: str
    ts: datetime = Field(default_factory=datetime.utcnow)


class ToolCall(BaseModel):
    name: str
    args: dict[str, Any] = Field(default_factory=dict)


class ConvState(BaseModel):
    """Single source of truth for one conversation turn."""

    # identity / context
    tenant_id: str
    conversation_id: str
    customer: CustomerCtx
    lang: Lang = Lang.AR

    # this turn's input
    inbound: InboundMessage
    text_norm: str = ""  # Arabizi-normalized + PII-redacted text

    # agent reasoning
    intent: Intent | None = None
    plan: list[ToolCall] = Field(default_factory=list)
    tool_results: dict[str, Any] = Field(default_factory=dict)
    needs_replan: bool = False
    hops: int = 0

    # durable-ish conversation memory (rehydrated each turn)
    cart: Cart = Field(default_factory=Cart)
    history: list[Turn] = Field(default_factory=list)
    summary: str = ""

    # output
    outbound: OutboundMessage | None = None
    escalate: bool = False

    # cross-cutting
    pii_map: dict[str, str] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    scratch: dict[str, Any] = Field(default_factory=dict)

    model_config = {"arbitrary_types_allowed": True}
