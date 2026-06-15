"""Table booking — checks real-time availability against the venue calendar."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from app.agent.state import ConvState
from app.deps import get_repos
from app.schemas.entities import ReservationRecord
from app.schemas.enums import ReservationStatus
from app.tools.base import ToolOutput, fail, ok

_PER_HOUR_CAPACITY = 10  # tables per area per hour


async def book_table(args: dict[str, Any], state: ConvState) -> ToolOutput:
    try:
        slot = datetime.fromisoformat(str(args["datetime"]))
    except (KeyError, ValueError):
        return fail("invalid or missing datetime")

    party = max(1, int(args.get("party_size", 2)))
    area = args.get("area", "indoor")

    repos = get_repos()
    taken = await repos.reservations.taken_slots(state.tenant_id, slot)
    same = [r for r in taken if r.slot.hour == slot.hour and r.area == area]
    if len(same) >= _PER_HOUR_CAPACITY:
        return ok(available=False, slot=args["datetime"], reason="full", area=area)

    rec = ReservationRecord(
        id="",
        tenant_id=state.tenant_id,
        customer_id=state.customer.id,
        party_size=party,
        slot=slot,
        area=area,
        occasion=args.get("occasion"),
        status=ReservationStatus.CONFIRMED,
    )
    rec = await repos.reservations.create(rec)
    return ok(
        available=True,
        reservation_id=rec.id,
        slot=args["datetime"],
        party_size=party,
        area=area,
        occasion=args.get("occasion"),
    )
