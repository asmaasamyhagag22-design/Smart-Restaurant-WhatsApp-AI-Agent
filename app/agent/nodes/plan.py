"""plan node — pick the next tool(s) to run.

A deterministic policy keyed on intent + what tools already ran + cart state.
(The docs describe an LLM planner; this policy is the reliable local default and
the clean seam where a Claude tool-selection call slots in for production.)
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any

from app.agent.state import ConvState, ToolCall
from app.schemas.enums import Intent
from app.services.text import extract_quantity, normalize_arabizi

_HOUR_RE = re.compile(r"(\d{1,2})")


def _parse_when(text: str) -> datetime | None:
    """Very small natural-time parser for the reservation demo."""
    t = normalize_arabizi(text)
    now = datetime.now()
    day = now
    if "بكره" in t or "بكرة" in t or "tomorrow" in t.lower():
        day = now + timedelta(days=1)
    elif "النهارده" in t or "today" in t.lower():
        day = now
    else:
        return None
    hour = 20
    m = re.search(r"الساعه\s*(\d{1,2})", t) or re.search(r"\bat\s*(\d{1,2})", t.lower())
    if m:
        hour = int(m.group(1))
        if hour < 10:  # assume evening for small numbers
            hour += 12
    return day.replace(hour=hour, minute=0, second=0, microsecond=0)


async def plan_node(state: ConvState) -> dict[str, Any]:
    iid = state.inbound.interactive_id
    tr = state.tool_results
    text = state.text_norm

    # ── interactive shortcuts ─────────────────────────────────────────
    if iid:
        if iid.startswith("add::"):
            sku = iid.split("::", 1)[1]
            return {"plan": [ToolCall(name="update_cart", args={"action": "add", "sku": sku, "qty": 1})]}
        if iid == "cancel_order":
            return {"plan": [ToolCall(name="update_cart", args={"action": "clear"})]}
        if iid == "pay_cod":
            return {"plan": [ToolCall(name="create_payment", args={"method": "cod"})]}
        if iid == "pay_card":
            return {"plan": [ToolCall(name="create_payment", args={"method": "card"})]}
        if iid == "show_menu":
            return {"plan": [ToolCall(name="query_menu", args={"query": "المنيو", "k": 8})]}
        if iid in ("confirm_order", "add_more"):
            return {"plan": []}  # respond handles these

    intent = state.intent
    plan: list[ToolCall] = []

    if intent == Intent.ORDER:
        if "order_items" not in tr:
            plan = [ToolCall(name="order_items", args={"text": text})]
    elif intent == Intent.BROWSE:
        if "query_menu" not in tr:
            plan = [ToolCall(name="query_menu", args={"query": text, "k": 6})]
    elif intent == Intent.RESERVE:
        when = _parse_when(text)
        if when:
            plan = [
                ToolCall(
                    name="book_table",
                    args={
                        "datetime": when.isoformat(),
                        "party_size": extract_quantity(text, default=2),
                        "area": "outdoor" if ("بره" in text or "outdoor" in text.lower()) else "indoor",
                    },
                )
            ]
    elif intent == Intent.TRACK:
        plan = [ToolCall(name="track_order", args={})]
    elif intent in (Intent.SUPPORT, Intent.ESCALATE):
        plan = [ToolCall(name="escalate_to_human", args={"reason": text[:120] or "support"})]
    # PAY (typed) and SMALLTALK fall through to respond with no tools

    return {"plan": plan}
