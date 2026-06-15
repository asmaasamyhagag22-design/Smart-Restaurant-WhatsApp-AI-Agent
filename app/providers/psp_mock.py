"""Mock payment provider — simulates a tokenized link + webhook locally."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from app.config import settings
from app.providers.base import BasePSP
from app.schemas.domain import PaymentLink
from app.schemas.entities import CustomerRecord
from app.schemas.enums import PaymentStatus

_STATUS = {
    "paid": PaymentStatus.PAID,
    "failed": PaymentStatus.FAILED,
    "refunded": PaymentStatus.REFUNDED,
}


class MockPSP(BasePSP):
    name = "mock"

    async def create_payment_link(
        self,
        *,
        amount_cents: int,
        reference: str,
        customer: CustomerRecord,
        return_url: str,
        description: str = "",
    ) -> PaymentLink:
        url = f"{settings.public_base_url}/pay/mock/{reference}"
        return PaymentLink(
            url=url,
            provider="mock",
            amount_cents=amount_cents,
            reference=reference,
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )

    def parse_webhook(self, payload: dict[str, Any]) -> tuple[str, PaymentStatus]:
        ref = payload.get("reference") or payload.get("ref") or ""
        status = str(payload.get("status", "paid")).lower()
        return ref, _STATUS.get(status, PaymentStatus.PENDING)
