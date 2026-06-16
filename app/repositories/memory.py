"""In-memory repository implementations — the local-default system of record."""
from __future__ import annotations

import uuid

from app.clock import now_utc
from app.repositories.base import (
    ConversationRepo,
    CustomerRepo,
    MenuRepo,
    OrderRepo,
    Repos,
    ReservationRepo,
    TenantRepo,
)
from app.schemas.entities import (
    ConversationRecord,
    CustomerRecord,
    MenuItemRecord,
    OrderRecord,
    ReservationRecord,
    TenantRecord,
)
from app.schemas.enums import ConversationStatus, OrderStatus, PaymentStatus


def _id() -> str:
    return uuid.uuid4().hex


class MemoryTenantRepo(TenantRepo):
    def __init__(self) -> None:
        self._d: dict[str, TenantRecord] = {}

    async def get(self, tenant_id: str) -> TenantRecord | None:
        return self._d.get(tenant_id)

    async def get_by_slug(self, slug: str) -> TenantRecord | None:
        return next((t for t in self._d.values() if t.slug == slug), None)

    async def get_by_phone(self, phone: str) -> TenantRecord | None:
        return next((t for t in self._d.values() if t.whatsapp_phone == phone), None)

    async def upsert(self, rec: TenantRecord) -> TenantRecord:
        if not rec.id:
            rec.id = _id()
        self._d[rec.id] = rec
        return rec

    async def list(self) -> list[TenantRecord]:
        return list(self._d.values())


class MemoryCustomerRepo(CustomerRepo):
    def __init__(self) -> None:
        self._d: dict[str, CustomerRecord] = {}

    async def get(self, customer_id: str) -> CustomerRecord | None:
        return self._d.get(customer_id)

    async def get_or_create(self, tenant_id: str, phone: str) -> CustomerRecord:
        for c in self._d.values():
            if c.tenant_id == tenant_id and c.phone == phone:
                return c
        rec = CustomerRecord(id=_id(), tenant_id=tenant_id, phone=phone)
        self._d[rec.id] = rec
        return rec

    async def update(self, rec: CustomerRecord) -> CustomerRecord:
        self._d[rec.id] = rec
        return rec


class MemoryMenuRepo(MenuRepo):
    def __init__(self) -> None:
        self._d: dict[str, MenuItemRecord] = {}

    async def get(self, tenant_id: str, item_id: str) -> MenuItemRecord | None:
        r = self._d.get(item_id)
        return r if r and r.tenant_id == tenant_id else None

    async def get_by_sku(self, tenant_id: str, sku: str) -> MenuItemRecord | None:
        return next(
            (r for r in self._d.values() if r.tenant_id == tenant_id and r.sku == sku), None
        )

    async def list(self, tenant_id: str) -> list[MenuItemRecord]:
        return [r for r in self._d.values() if r.tenant_id == tenant_id]

    async def upsert(self, rec: MenuItemRecord) -> MenuItemRecord:
        if not rec.id:
            rec.id = _id()
        self._d[rec.id] = rec
        return rec

    async def set_stock(self, tenant_id: str, item_id: str, in_stock: bool) -> None:
        r = self._d.get(item_id)
        if r and r.tenant_id == tenant_id:
            r.in_stock = in_stock


class MemoryConversationRepo(ConversationRepo):
    def __init__(self) -> None:
        self._d: dict[str, ConversationRecord] = {}

    async def get(self, conversation_id: str) -> ConversationRecord | None:
        return self._d.get(conversation_id)

    async def get_active(self, tenant_id: str, customer_id: str) -> ConversationRecord | None:
        return next(
            (
                c
                for c in self._d.values()
                if c.tenant_id == tenant_id
                and c.customer_id == customer_id
                and c.status == ConversationStatus.ACTIVE
            ),
            None,
        )

    async def create(self, tenant_id: str, customer_id: str) -> ConversationRecord:
        rec = ConversationRecord(
            id=_id(), tenant_id=tenant_id, customer_id=customer_id, state={}
        )
        self._d[rec.id] = rec
        return rec

    async def save_state(
        self, conversation_id: str, state: dict, status: ConversationStatus
    ) -> None:
        rec = self._d.get(conversation_id)
        if rec:
            rec.state = state
            rec.status = status
            rec.last_activity = now_utc()

    async def list(
        self,
        tenant_id: str,
        status: ConversationStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ConversationRecord]:
        items = [
            c
            for c in self._d.values()
            if c.tenant_id == tenant_id and (status is None or c.status == status)
        ]
        items.sort(key=lambda c: c.last_activity, reverse=True)
        return items[offset : offset + limit]


class MemoryOrderRepo(OrderRepo):
    def __init__(self) -> None:
        self._d: dict[str, OrderRecord] = {}

    async def create(self, rec: OrderRecord) -> OrderRecord:
        if not rec.id:
            rec.id = _id()
        self._d[rec.id] = rec
        return rec

    async def get(self, order_id: str) -> OrderRecord | None:
        return self._d.get(order_id)

    async def get_by_reference(self, reference: str) -> OrderRecord | None:
        return next((o for o in self._d.values() if o.payment_reference == reference), None)

    async def update_status(
        self,
        order_id: str,
        status: OrderStatus | None = None,
        payment_status: PaymentStatus | None = None,
        pos_order_id: str | None = None,
    ) -> OrderRecord | None:
        o = self._d.get(order_id)
        if not o:
            return None
        if status is not None:
            o.status = status
        if payment_status is not None:
            o.payment_status = payment_status
        if pos_order_id is not None:
            o.pos_order_id = pos_order_id
        return o

    async def recent_for_customer(
        self, tenant_id: str, customer_id: str, limit: int = 10
    ) -> list[OrderRecord]:
        items = [
            o
            for o in self._d.values()
            if o.tenant_id == tenant_id and o.customer_id == customer_id
        ]
        items.sort(key=lambda o: o.created_at, reverse=True)
        return items[:limit]


class MemoryReservationRepo(ReservationRepo):
    def __init__(self) -> None:
        self._d: dict[str, ReservationRecord] = {}

    async def create(self, rec: ReservationRecord) -> ReservationRecord:
        if not rec.id:
            rec.id = _id()
        self._d[rec.id] = rec
        return rec

    async def get(self, reservation_id: str) -> ReservationRecord | None:
        return self._d.get(reservation_id)

    async def taken_slots(self, tenant_id: str, day: datetime) -> list[ReservationRecord]:
        return [
            r
            for r in self._d.values()
            if r.tenant_id == tenant_id and r.slot.date() == day.date()
        ]


def build_memory_repos() -> Repos:
    return Repos(
        tenants=MemoryTenantRepo(),
        customers=MemoryCustomerRepo(),
        menu=MemoryMenuRepo(),
        conversations=MemoryConversationRepo(),
        orders=MemoryOrderRepo(),
        reservations=MemoryReservationRepo(),
    )
