"""The six core tools (+ allergen/eta/escalation helpers) the agent can call.

``TOOLS`` maps a tool name to its implementation. ``TOOL_SPECS`` are the
Anthropic-style schemas the planner chooses from. Implementations live in the
sibling leaf modules; this registry is the single source of truth for names.
"""
from __future__ import annotations

from typing import Any

from app.tools.base import ToolFn, ToolOutput, fail, ok
from app.tools.cart import update_cart
from app.tools.escalation import escalate_to_human
from app.tools.menu_rag import check_allergens, query_menu
from app.tools.payments import create_payment
from app.tools.recommender import recommend
from app.tools.reservations import book_table
from app.tools.tracking import check_eta, track_order

TOOLS: dict[str, ToolFn] = {
    "query_menu": query_menu,
    "check_allergens": check_allergens,
    "update_cart": update_cart,
    "book_table": book_table,
    "create_payment": create_payment,
    "track_order": track_order,
    "check_eta": check_eta,
    "recommend": recommend,
    "escalate_to_human": escalate_to_human,
}

TOOL_SPECS: list[dict[str, Any]] = [
    {
        "name": "query_menu",
        "description": "Search the live menu (RAG). ALWAYS use this before quoting any item or price.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "what the user wants"},
                "diet": {"type": "array", "items": {"type": "string"}},
                "exclude_allergens": {"type": "array", "items": {"type": "string"}},
                "max_price_cents": {"type": ["integer", "null"]},
                "spice_max": {"type": "integer", "minimum": 0, "maximum": 5},
                "k": {"type": "integer", "minimum": 1, "maximum": 20},
            },
            "required": ["query"],
        },
    },
    {
        "name": "check_allergens",
        "description": "Return the allergen list for a specific menu item. Required for any allergy question.",
        "input_schema": {
            "type": "object",
            "properties": {"sku": {"type": "string"}, "item_id": {"type": "string"}},
        },
    },
    {
        "name": "update_cart",
        "description": "Add/remove/set/clear cart items by SKU.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["add", "remove", "set", "clear"]},
                "sku": {"type": "string"},
                "qty": {"type": "integer", "minimum": 0},
                "modifiers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name_ar": {"type": "string"},
                            "name_en": {"type": "string"},
                            "price_delta_cents": {"type": "integer"},
                        },
                    },
                },
                "notes": {"type": "string"},
            },
            "required": ["action"],
        },
    },
    {
        "name": "book_table",
        "description": "Book a table. Checks real-time availability for party size / area / time.",
        "input_schema": {
            "type": "object",
            "properties": {
                "party_size": {"type": "integer", "minimum": 1, "maximum": 50},
                "datetime": {"type": "string", "description": "ISO 8601 date-time"},
                "area": {"type": "string", "enum": ["indoor", "outdoor"]},
                "occasion": {"type": "string"},
            },
            "required": ["party_size", "datetime"],
        },
    },
    {
        "name": "create_payment",
        "description": "Generate a tokenized payment link or register COD for the current cart.",
        "input_schema": {
            "type": "object",
            "properties": {"method": {"type": "string", "enum": ["card", "cod", "wallet"]}},
            "required": ["method"],
        },
    },
    {
        "name": "track_order",
        "description": "Look up live status/ETA for an order (latest order if id omitted).",
        "input_schema": {
            "type": "object",
            "properties": {"order_id": {"type": ["string", "null"]}},
        },
    },
    {
        "name": "check_eta",
        "description": "Estimate delivery time for the customer's zone. Never promise a time without it.",
        "input_schema": {"type": "object", "properties": {"zone": {"type": "string"}}},
    },
    {
        "name": "recommend",
        "description": "Personalized dish recommendations from history + dietary tags.",
        "input_schema": {
            "type": "object",
            "properties": {"k": {"type": "integer", "minimum": 1, "maximum": 10}},
        },
    },
    {
        "name": "escalate_to_human",
        "description": "Hand the conversation to a human operator. Use when unsure or asked.",
        "input_schema": {
            "type": "object",
            "properties": {"reason": {"type": "string"}},
            "required": ["reason"],
        },
    },
]

__all__ = ["TOOLS", "TOOL_SPECS", "ToolFn", "ToolOutput", "ok", "fail"]
