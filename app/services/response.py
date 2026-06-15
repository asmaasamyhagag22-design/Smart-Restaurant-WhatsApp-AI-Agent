"""Outbound dispatcher — send with a small retry budget (docs §07)."""
from __future__ import annotations

import asyncio

from app.deps import get_channel
from app.logging_conf import get_logger
from app.schemas.messaging import OutboundMessage

log = get_logger("response")


async def dispatch(msg: OutboundMessage, retries: int = 3) -> bool:
    channel = get_channel()
    for attempt in range(retries):
        try:
            await channel.send(msg)
            return True
        except Exception as e:
            log.warning("dispatch_retry", attempt=attempt + 1, error=str(e)[:120])
            await asyncio.sleep(0.2 * (attempt + 1))
    return False
