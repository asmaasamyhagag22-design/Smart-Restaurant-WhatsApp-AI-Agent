"""reflect node — sanity check + decide whether to replan (docs §06.1).

For an ORDER turn we search the menu first, then loop back once to add the best
match to the cart. Cart totals are always recomputed from line items (no float
drift), so price reconciliation is structural rather than a separate check.
"""
from __future__ import annotations

from typing import Any

from app.agent.state import ConvState
from app.schemas.enums import Intent


async def reflect_node(state: ConvState) -> dict[str, Any]:
    qm = state.tool_results.get("query_menu")
    wants_add = (
        state.intent == Intent.ORDER
        and state.cart.is_empty
        and bool(qm and qm.get("matches"))
        and "update_cart" not in state.tool_results
    )
    return {"needs_replan": wants_add}
