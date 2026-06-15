"""tools node — the deterministic execution engine.

Runs the planned tool calls in order on a working copy of the state so that a
later tool in the same plan sees the cart changes made by an earlier one. Tools
never raise into the graph: failures are captured as errors and the reflect node
decides whether to replan.
"""
from __future__ import annotations

from typing import Any

from app.agent.state import ConvState
from app.logging_conf import get_logger
from app.tools import TOOLS

log = get_logger("agent.tools")


async def tools_node(state: ConvState) -> dict[str, Any]:
    results: dict[str, Any] = dict(state.tool_results)
    errors: list[str] = list(state.errors)
    working = state.model_copy(deep=True)
    escalate = state.escalate

    for call in state.plan:
        fn = TOOLS.get(call.name)
        if fn is None:
            errors.append(f"unknown tool: {call.name}")
            continue
        try:
            out = await fn(call.args, working)
        except Exception as e:  # a buggy tool must not crash the conversation
            log.error("tool_failed", tool=call.name, error=str(e))
            errors.append(f"{call.name}: {e}")
            continue

        results[call.name] = out.data
        if out.cart is not None:
            working.cart = out.cart
        if out.escalate:
            escalate = True
        if out.error:
            errors.append(f"{call.name}: {out.error}")

    return {
        "tool_results": results,
        "cart": working.cart,
        "escalate": escalate,
        "errors": errors,
        "hops": state.hops + 1,
    }
