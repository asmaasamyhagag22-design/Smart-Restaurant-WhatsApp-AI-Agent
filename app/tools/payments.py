"""Payments — register COD or generate a tokenized payment link (PCI scope zero)."""
from __future__ import annotations

import uuid
from typing import Any

from app.agent.state import ConvState
from app.config import settings
from app.deps import get_psp, get_repos
from app.schemas.domain import Cart
from app.schemas.entities import CustomerRecord, OrderRecord
from app.schemas.enums import Fulfillment, OrderStatus, PaymentStatus
from app.tools.base import ToolOutput, fail, ok


async def create_payment(args: dict[str, Any], state: ConvState) -> ToolOutput:
    if state.cart.is_empty:
        return fail("cart is empty")

    repos = get_repos()
    method = args.get("method", "cod")
    reference = "ord_" + uuid.uuid4().hex[:12]

    order = OrderRecord(
        id="",
        tenant_id=state.tenant_id,
        customer_id=state.customer.id,
        conversation_id=state.conversation_id,
        items=[i.model_dump() for i in state.cart.items],
        subtotal_cents=state.cart.subtotal_cents,
        delivery_cents=state.cart.delivery_fee_cents,
        discount_cents=state.cart.discount_cents,
        total_cents=state.cart.total_cents,
        fulfillment=Fulfillment.DELIVERY,
        payment_status=PaymentStatus.PENDING,
        status=OrderStatus.PLACED,
        payment_reference=reference,
    )
    order = await repos.orders.create(order)

    if method == "cod":
        # order is placed → start the conversation's cart fresh
        return ok(
            cart=Cart(),
            method="cod",
            order_id=order.id,
            reference=reference,
            total_cents=order.total_cents,
            payment_status="pending",
            paid=False,
        )

    psp = get_psp()
    customer = await repos.customers.get(state.customer.id) or CustomerRecord(
        id=state.customer.id, tenant_id=state.tenant_id, phone=state.customer.phone
    )
    link = await psp.create_payment_link(
        amount_cents=order.total_cents,
        reference=reference,
        customer=customer,
        return_url=f"{settings.public_base_url}/pay/return",
        description=f"Order {reference}",
    )
    return ok(
        cart=Cart(),  # order placed (pending payment) → reset the cart
        method=method,
        order_id=order.id,
        reference=reference,
        total_cents=order.total_cents,
        payment_url=link.url,
        paid=False,
    )
