"""Domain value objects used by the agent and tools.

Money is handled in integer **piastres** (1 EGP = 100) everywhere to avoid float
drift — price correctness is a hard requirement (see docs §10). Formatting to a
human string happens only at render time via :func:`format_money`.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.enums import Fulfillment, Lang


def format_money(cents: int, lang: Lang = Lang.AR) -> str:
    """Render piastres as a localized price string, e.g. ``85 ج`` / ``85 EGP``."""
    egp = cents / 100
    s = f"{egp:.0f}" if cents % 100 == 0 else f"{egp:.2f}"
    return f"{s} ج" if lang == Lang.AR else f"{s} EGP"


# ── Menu retrieval (RAG) ──────────────────────────────────────────────
class MenuQuery(BaseModel):
    """Typed query the agent hands to the menu RAG tool."""

    query: str = Field(..., description="what the user is looking for")
    diet: list[str] = Field(default_factory=list, description="halal|vegan|vegetarian")
    exclude_allergens: list[str] = Field(default_factory=list)
    max_price_cents: int | None = None
    spice_max: int = Field(3, ge=0, le=5)
    k: int = Field(5, ge=1, le=20)


class MenuMatch(BaseModel):
    item_id: str
    sku: str
    name_ar: str
    name_en: str
    description: str = ""
    price_cents: int
    allergens: list[str] = Field(default_factory=list)
    diet_tags: list[str] = Field(default_factory=list)
    spice_level: int = 0
    in_stock: bool = True
    score: float = 0.0


# ── Cart ──────────────────────────────────────────────────────────────
class Modifier(BaseModel):
    name_ar: str = ""
    name_en: str = ""
    price_delta_cents: int = 0


class CartItem(BaseModel):
    item_id: str
    sku: str
    name_ar: str
    name_en: str
    qty: int = Field(1, ge=1)
    unit_price_cents: int
    modifiers: list[Modifier] = Field(default_factory=list)
    notes: str = ""

    @property
    def line_total_cents(self) -> int:
        per = self.unit_price_cents + sum(m.price_delta_cents for m in self.modifiers)
        return max(0, per) * self.qty

    def display_name(self, lang: Lang = Lang.AR) -> str:
        base = self.name_ar if lang == Lang.AR else self.name_en
        if self.modifiers:
            mods = ", ".join((m.name_ar if lang == Lang.AR else m.name_en) for m in self.modifiers)
            return f"{base} ({mods})"
        return base


class Cart(BaseModel):
    items: list[CartItem] = Field(default_factory=list)
    delivery_fee_cents: int = 0
    discount_cents: int = 0
    currency: str = "EGP"

    @property
    def subtotal_cents(self) -> int:
        return sum(i.line_total_cents for i in self.items)

    @property
    def total_cents(self) -> int:
        return max(0, self.subtotal_cents + self.delivery_fee_cents - self.discount_cents)

    @property
    def is_empty(self) -> bool:
        return not self.items


# ── Payments / tracking / reservations / recs ─────────────────────────
class PaymentLink(BaseModel):
    url: str
    provider: str
    amount_cents: int
    reference: str
    expires_at: datetime | None = None


class ETAInfo(BaseModel):
    minutes: int
    status: str = "preparing"
    courier_name: str | None = None
    map_url: str | None = None


class ReservationRequest(BaseModel):
    party_size: int = Field(..., ge=1, le=50)
    slot: datetime
    area: str = "indoor"  # indoor | outdoor
    occasion: str | None = None
    fulfillment: Fulfillment = Fulfillment.DINE_IN


class Recommendation(BaseModel):
    items: list[MenuMatch] = Field(default_factory=list)
    reason_ar: str = ""
    reason_en: str = ""
