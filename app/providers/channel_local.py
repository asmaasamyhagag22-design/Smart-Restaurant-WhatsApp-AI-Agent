"""Local channel — backs the built-in web chat simulator.

Replies are returned synchronously by the ``/chat`` endpoint, so ``send`` only
needs to record outbound messages (useful for a polling client / debugging).
"""
from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

from app.logging_conf import get_logger
from app.providers.base import BaseChannel
from app.schemas.enums import MessageType
from app.schemas.messaging import InboundMessage, OutboundMessage

log = get_logger("channel.local")


class LocalChannel(BaseChannel):
    name = "local"

    def __init__(self) -> None:
        self.outbox: dict[str, deque[OutboundMessage]] = defaultdict(lambda: deque(maxlen=50))

    async def send(self, msg: OutboundMessage) -> None:
        self.outbox[msg.to].append(msg)
        log.info("local_send", to=msg.to, text=msg.text[:80])

    def parse_inbound(self, payload: dict[str, Any], tenant_id: str) -> list[InboundMessage]:
        try:
            mtype = MessageType(payload.get("type", "text"))
        except ValueError:
            mtype = MessageType.TEXT
        return [
            InboundMessage(
                tenant_id=tenant_id,
                channel="local",
                from_phone=payload.get("from", "+20-local-tester"),
                type=mtype,
                text=payload.get("text", ""),
                interactive_id=payload.get("interactive_id"),
                latitude=payload.get("latitude"),
                longitude=payload.get("longitude"),
                media_url=payload.get("media_url"),
                media_id=payload.get("media_id"),
                raw=payload,
            )
        ]
