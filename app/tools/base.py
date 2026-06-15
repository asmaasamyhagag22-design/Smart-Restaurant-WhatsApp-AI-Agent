"""Tool calling convention.

A tool is ``async def fn(args: dict, state: ConvState) -> ToolOutput``. Tools are
pure-ish: they may read repositories/providers and return data + an optionally
updated cart, but they never send messages or mutate ``state`` directly. The
tools node applies the returned cart/escalate flags to the conversation state.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel, Field

from app.agent.state import ConvState
from app.schemas.domain import Cart


class ToolOutput(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict)
    cart: Cart | None = None  # set when the tool modifies the cart
    escalate: bool = False
    error: str | None = None

    model_config = {"arbitrary_types_allowed": True}


ToolFn = Callable[[dict[str, Any], ConvState], Awaitable[ToolOutput]]


def ok(cart: Cart | None = None, **data: Any) -> ToolOutput:
    return ToolOutput(data=data, cart=cart)


def fail(message: str) -> ToolOutput:
    return ToolOutput(error=message)
