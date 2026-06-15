"""Personalized recommendations — history + dietary tags (docs §04 F·06)."""
from __future__ import annotations

from collections import Counter
from typing import Any

from app.agent.state import ConvState
from app.deps import get_repos
from app.tools.base import ToolOutput, ok


def _to_match(it: Any) -> dict[str, Any]:
    return {
        "item_id": it.id,
        "sku": it.sku,
        "name_ar": it.name_ar,
        "name_en": it.name_en,
        "description": it.description,
        "price_cents": it.price_cents,
        "allergens": it.allergens,
        "diet_tags": it.diet_tags,
        "spice_level": it.spice_level,
        "in_stock": it.in_stock,
        "score": 1.0,
    }


async def recommend(args: dict[str, Any], state: ConvState) -> ToolOutput:
    repos = get_repos()
    k = max(1, int(args.get("k", 3)))

    recent = await repos.orders.recent_for_customer(state.tenant_id, state.customer.id, 10)
    items = await repos.menu.list(state.tenant_id)
    by_sku = {i.sku: i for i in items if i.in_stock}

    # 1) most-frequently ordered, still-available items
    freq: Counter[str] = Counter()
    for o in recent:
        for line in o.items:
            sku = line.get("sku")
            if sku in by_sku:
                freq[sku] += line.get("qty", 1)

    picks: list[Any] = [by_sku[sku] for sku, _ in freq.most_common(k)]

    # 2) honour dietary flags, then fill from the rest of the menu
    diet = set(state.customer.diet_tags)
    if len(picks) < k:
        for it in items:
            if it in picks or not it.in_stock:
                continue
            if diet and not diet.issubset(set(it.diet_tags)):
                continue
            picks.append(it)
            if len(picks) >= k:
                break

    return ok(matches=[_to_match(i) for i in picks[:k]], based_on_orders=len(recent))
