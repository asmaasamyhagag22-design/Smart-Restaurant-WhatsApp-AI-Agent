"""Enumerations shared across the agent, tools and storage."""
from __future__ import annotations

from enum import Enum


class Lang(str, Enum):
    AR = "ar-EG"
    EN = "en"


class Intent(str, Enum):
    ORDER = "order"
    BROWSE = "browse"
    RESERVE = "reserve"
    TRACK = "track"
    PAY = "pay"
    SUPPORT = "support"
    SMALLTALK = "smalltalk"
    ESCALATE = "escalate"


class Fulfillment(str, Enum):
    DELIVERY = "delivery"
    PICKUP = "pickup"
    DINE_IN = "dine_in"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class OrderStatus(str, Enum):
    CART = "cart"
    PLACED = "placed"
    CONFIRMED = "confirmed"
    PREPARING = "preparing"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class ReservationStatus(str, Enum):
    REQUESTED = "requested"
    CONFIRMED = "confirmed"
    SEATED = "seated"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class MessageType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    LOCATION = "location"
    INTERACTIVE = "interactive"
    TEMPLATE = "template"


class ConversationStatus(str, Enum):
    ACTIVE = "active"
    ESCALATED = "escalated"
    CLOSED = "closed"
