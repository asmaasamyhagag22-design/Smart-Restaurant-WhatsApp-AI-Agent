"""Channel-agnostic message envelopes.

Inbound and outbound messages are normalized here so the agent core never sees
WhatsApp-specific JSON. Channel adapters (local simulator, Meta Cloud API)
translate to/from these shapes.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.clock import now_utc
from app.schemas.enums import MessageType


# ── Inbound ───────────────────────────────────────────────────────────
class InboundMessage(BaseModel):
    tenant_id: str
    channel: str = "local"  # local | whatsapp
    from_phone: str
    wa_message_id: str | None = None
    type: MessageType = MessageType.TEXT
    text: str = ""
    media_id: str | None = None
    media_url: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    # id of the button/list option the user tapped (interactive replies)
    interactive_id: str | None = None
    timestamp: datetime = Field(default_factory=now_utc)
    raw: dict[str, Any] = Field(default_factory=dict)


# ── Outbound ──────────────────────────────────────────────────────────
class Button(BaseModel):
    id: str
    title: str  # <= 20 chars for WhatsApp


class ListRow(BaseModel):
    id: str
    title: str
    description: str = ""


class ListSection(BaseModel):
    title: str
    rows: list[ListRow] = Field(default_factory=list)


class OutboundMessage(BaseModel):
    """A reply the channel adapter renders to its own wire format."""

    to: str
    text: str = ""
    rtl: bool = True
    image_url: str | None = None
    buttons: list[Button] = Field(default_factory=list)
    list_button_text: str = ""
    list_sections: list[ListSection] = Field(default_factory=list)
    # free-form metadata for telemetry / the local UI (e.g. tools used)
    meta: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_interactive(self) -> bool:
        return bool(self.buttons or self.list_sections)
