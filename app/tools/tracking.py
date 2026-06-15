"""Order tracking + delivery ETA."""
from __future__ import annotations

from typing import Any

from app.agent.state import ConvState
from app.deps import get_repos
from app.schemas.enums import OrderStatus
from app.tools.base import ToolOutput, ok

_ETA_BY_STATUS = {
    OrderStatus.PLACED: 40,
    OrderStatus.CONFIRMED: 35,
    OrderStatus.PREPARING: 25,
    OrderStatus.OUT_FOR_DELIVERY: 12,
    OrderStatus.DELIVERED: 0,
}


async def track_order(args: dict[str, Any], state: ConvState) -> ToolOutput:
    repos = get_repos()
    order = None
    if args.get("order_id"):
        order = await repos.orders.get(args["order_id"])
    if not order:
        recent = await repos.orders.recent_for_customer(state.tenant_id, state.customer.id, 1)
        order = recent[0] if recent else None
    if not order:
        return ok(found=False)

    eta = _ETA_BY_STATUS.get(order.status, 30)
    courier = "كريم" if order.status == OrderStatus.OUT_FOR_DELIVERY else None
    return ok(
        found=True,
        order_id=order.id,
        status=order.status.value,
        payment_status=order.payment_status.value,
        eta_minutes=eta,
        courier=courier,
    )


async def check_eta(args: dict[str, Any], state: ConvState) -> ToolOutput:
    zone = args.get("zone") or state.customer.zone or "unknown"
    base = 35 if zone == "unknown" else 30
    return ok(zone=zone, eta_minutes=base)
