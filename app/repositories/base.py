"""Repository interfaces + the :class:`Repos` aggregate."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from app.schemas.entities import (
    ConversationRecord,
    CustomerRecord,
    MenuItemRecord,
    OrderRecord,
    ReservationRecord,
    TenantRecord,
)
from app.schemas.enums import ConversationStatus, OrderStatus, PaymentStatus


class TenantRepo(ABC):
    @abstractmethod
    async def get(self, tenant_id: str) -> TenantRecord | None: ...
    @abstractmethod
    async def get_by_slug(self, slug: str) -> TenantRecord | None: ...
    @abstractmethod
    async def get_by_phone(self, phone: str) -> TenantRecord | None: ...
    @abstractmethod
    async def upsert(self, rec: TenantRecord) -> TenantRecord: ...
    @abstractmethod
    async def list(self) -> list[TenantRecord]: ...


class CustomerRepo(ABC):
    @abstractmethod
    async def get(self, customer_id: str) -> CustomerRecord | None: ...
    @abstractmethod
    async def get_or_create(self, tenant_id: str, phone: str) -> CustomerRecord: ...
    @abstractmethod
    async def update(self, rec: CustomerRecord) -> CustomerRecord: ...


class MenuRepo(ABC):
    @abstractmethod
    async def get(self, tenant_id: str, item_id: str) -> MenuItemRecord | None: ...
    @abstractmethod
    async def get_by_sku(self, tenant_id: str, sku: str) -> MenuItemRecord | None: ...
    @abstractmethod
    async def list(self, tenant_id: str) -> list[MenuItemRecord]: ...
    @abstractmethod
    async def upsert(self, rec: MenuItemRecord) -> MenuItemRecord: ...
    @abstractmethod
    async def set_stock(self, tenant_id: str, item_id: str, in_stock: bool) -> None: ...


class ConversationRepo(ABC):
    @abstractmethod
    async def get(self, conversation_id: str) -> ConversationRecord | None: ...
    @abstractmethod
    async def get_active(self, tenant_id: str, customer_id: str) -> ConversationRecord | None: ...
    @abstractmethod
    async def create(self, tenant_id: str, customer_id: str) -> ConversationRecord: ...
    @abstractmethod
    async def save_state(
        self, conversation_id: str, state: dict, status: ConversationStatus
    ) -> None: ...
    @abstractmethod
    async def list(
        self, tenant_id: str, status: ConversationStatus | None = None, limit: int = 50, offset: int = 0
    ) -> list[ConversationRecord]: ...


class OrderRepo(ABC):
    @abstractmethod
    async def create(self, rec: OrderRecord) -> OrderRecord: ...
    @abstractmethod
    async def get(self, order_id: str) -> OrderRecord | None: ...
    @abstractmethod
    async def get_by_reference(self, reference: str) -> OrderRecord | None: ...
    @abstractmethod
    async def update_status(
        self,
        order_id: str,
        status: OrderStatus | None = None,
        payment_status: PaymentStatus | None = None,
        pos_order_id: str | None = None,
    ) -> OrderRecord | None: ...
    @abstractmethod
    async def recent_for_customer(
        self, tenant_id: str, customer_id: str, limit: int = 10
    ) -> list[OrderRecord]: ...


class ReservationRepo(ABC):
    @abstractmethod
    async def create(self, rec: ReservationRecord) -> ReservationRecord: ...
    @abstractmethod
    async def get(self, reservation_id: str) -> ReservationRecord | None: ...
    @abstractmethod
    async def taken_slots(self, tenant_id: str, day: datetime) -> list[ReservationRecord]: ...


@dataclass
class Repos:
    """Bundle of all repositories handed to tools and services."""

    tenants: TenantRepo
    customers: CustomerRepo
    menu: MenuRepo
    conversations: ConversationRepo
    orders: OrderRepo
    reservations: ReservationRepo
