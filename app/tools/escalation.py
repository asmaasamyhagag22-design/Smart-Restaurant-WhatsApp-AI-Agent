"""Human escalation — flips the conversation to operator takeover (docs §04 F·10)."""
from __future__ import annotations

from typing import Any

from app.agent.state import ConvState
from app.tools.base import ToolOutput


async def escalate_to_human(args: dict[str, Any], state: ConvState) -> ToolOutput:
    return ToolOutput(data={"reason": args.get("reason", "user requested")}, escalate=True)
