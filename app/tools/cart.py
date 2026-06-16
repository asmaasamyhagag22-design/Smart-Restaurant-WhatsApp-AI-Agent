"""Cart manager — add / remove / set / clear items by SKU."""
from __future__ import annotations

from typing import Any

from app.agent.state import ConvState
from app.deps import get_repos
from app.schemas.domain import CartItem, Modifier
from app.services.text import parse_order_lines
from app.tools.base import ToolOutput, fail, ok
from app.tools.menu_rag import search_menu


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


async def order_items(args: dict[str, Any], state: ConvState) -> ToolOutput:
    """Parse a free-text order into line items, resolve each against the menu
    (RAG), and add them all to the cart in one shot — supports multiple items,
    quantities and modifiers."""
    text = args.get("text") or state.text_norm or ""
    lines = parse_order_lines(text) or [{"qty": 1, "phrase": text, "modifiers": []}]

    cart = state.cart.model_copy(deep=True)
    added: list[str] = []
    notfound: list[str] = []

    for line in lines:
        matches = await search_menu(state.tenant_id, line["phrase"], k=1)
        if not matches:
            if line["phrase"]:
                notfound.append(line["phrase"])
            continue
        m = matches[0]
        mods = [Modifier(name_ar=x, name_en=x, price_delta_cents=0) for x in line["modifiers"]]
        existing = next(
            (i for i in cart.items if i.sku == m["sku"] and not i.modifiers and not mods), None
        )
        if existing:
            existing.qty += line["qty"]
        else:
            cart.items.append(
                CartItem(
                    item_id=m["item_id"],
                    sku=m["sku"],
                    name_ar=m["name_ar"],
                    name_en=m["name_en"],
                    qty=line["qty"],
                    unit_price_cents=m["price_cents"],
                    modifiers=mods,
                )
            )
        added.append(m["sku"])

    return ok(cart=cart, added=added, notfound=notfound, subtotal_cents=cart.subtotal_cents)
