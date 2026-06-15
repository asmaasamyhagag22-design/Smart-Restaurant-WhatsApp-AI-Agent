"""Cart manager — add / remove / set / clear items by SKU."""
from __future__ import annotations

from typing import Any

from app.agent.state import ConvState
from app.deps import get_repos
from app.schemas.domain import CartItem, Modifier
from app.tools.base import ToolOutput, fail, ok


async def update_cart(args: dict[str, Any], state: ConvState) -> ToolOutput:
    cart = state.cart.model_copy(deep=True)
    action = args.get("action", "add")

    if action == "clear":
        cart.items = []
        return ok(cart=cart, action="clear")

    sku = args.get("sku")
    if not sku:
        return fail("sku required")

    if action == "remove":
        cart.items = [i for i in cart.items if i.sku != sku]
        return ok(cart=cart, action="remove", sku=sku)

    repos = get_repos()
    item = await repos.menu.get_by_sku(state.tenant_id, sku)
    if not item:
        return fail(f"unknown sku: {sku}")
    if not item.in_stock:
        return ok(cart=cart, action="out_of_stock", sku=sku)

    qty = max(1, int(args.get("qty", 1)))
    mods = [Modifier(**m) for m in args.get("modifiers", [])]

    # merge with an identical line (same sku, no modifiers) when adding
    existing = next((i for i in cart.items if i.sku == sku and not i.modifiers), None)
    if action == "add" and existing and not mods:
        existing.qty += qty
    else:
        if action == "set":
            cart.items = [i for i in cart.items if i.sku != sku]
        cart.items.append(
            CartItem(
                item_id=item.id,
                sku=item.sku,
                name_ar=item.name_ar,
                name_en=item.name_en,
                qty=qty,
                unit_price_cents=item.price_cents,
                modifiers=mods,
                notes=args.get("notes", ""),
            )
        )

    return ok(cart=cart, action=action, sku=sku, subtotal_cents=cart.subtotal_cents)
