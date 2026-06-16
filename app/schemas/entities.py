"""Persisted records — the system of record (docs §08).

These mirror the SQL schema. The in-memory repository stores them directly; the
SQL repository maps SQLAlchemy rows onto them, so the rest of the app depends on
these Pydantic shapes, never on the storage engine.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.clock import now_utc as _utcnow
from app.schemas.enums import (
    ConversationStatus,
    Fulfillment,
    OrderStatus,
    PaymentStatus,
    ReservationStatus,
)


class TenantRecord(BaseModel):
    id: str
    slug: str
    name: str
    whatsapp_phone: str = ""
    persona_name: str = ""
    voice_guidelines: str = ""
    psp_provider: str = "mock"
    enabled_payments: list[str] = Field(default_factory=lambda: ["cod", "card"])
    persona: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_utcnow)


class CustomerRecord(BaseModel):
    id: str
    tenant_id: str
    phone: str
    name: str | None = None
    preferred_lang: str = "ar-EG"
    diet_tags: list[str] = Field(default_factory=list)
    ltv_cents: int = 0
    zone: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)


class MenuItemRecord(BaseModel):
    id: str
    tenant_id: str
    sku: str
    name_ar: str
    name_en: str
    description: str = ""
    category: str = ""
    price_cents: int = 0
    allergens: list[str] = Field(default_factory=list)
    diet_tags: list[str] = Field(default_factory=list)
    spice_level: int = 0
    in_stock: bool = True
    embedding_id: str | None = None


class ConversationRecord(BaseModel):
    id: str
    tenant_id: str
    customer_id: str
    state: dict[str, Any] = Field(default_factory=dict)
    status: ConversationStatus = ConversationStatus.ACTIVE
    last_activity: datetime = Field(default_factory=_utcnow)


class OrderRecord(BaseModel):
    id: str
    tenant_id: str
    customer_id: str
    conversation_id: str
    items: list[dict[str, Any]] = Field(default_factory=list)
    subtotal_cents: int = 0
    delivery_cents: int = 0
    discount_cents: int = 0
    total_cents: int = 0
    payment_status: PaymentStatus = PaymentStatus.PENDING
    fulfillment: Fulfillment = Fulfillment.DELIVERY
    status: OrderStatus = OrderStatus.PLACED
    pos_order_id: str | None = None
    payment_reference: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)


class ReservationRecord(BaseModel):
    id: str
    tenant_id: str
    customer_id: str
    party_size: int
    slot: datetime
    area: str = "indoor"
    occasion: str | None = None
    status: ReservationStatus = ReservationStatus.REQUESTED
    created_at: datetime = Field(default_factory=_utcnow)
