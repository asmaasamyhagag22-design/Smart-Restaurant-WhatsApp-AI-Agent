"""intent node — classify the turn into a typed intent + detect language.

Interactive button/list taps bypass the LLM (the id already encodes intent).
Otherwise the LLM returns structured ``{intent, lang}``; on any failure we fall
back to keyword heuristics so the graph never stalls.
"""
from __future__ import annotations

from typing import Any

from app.agent.state import ConvState
from app.config import settings
from app.deps import get_llm
from app.schemas.enums import Intent, Lang
from app.services.text import detect_lang, guess_intent

_BUTTON_INTENT: dict[str, Intent] = {
    "confirm_order": Intent.PAY,
    "pay_card": Intent.PAY,
    "pay_cod": Intent.PAY,
    "pay_wallet": Intent.PAY,
    "add_more": Intent.BROWSE,
    "cancel_order": Intent.SMALLTALK,
}

_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "intent": {"type": "string", "enum": [i.value for i in Intent]},
        "lang": {"type": "string", "enum": [l.value for l in Lang]},
    },
    "required": ["intent", "lang"],
}

_SYSTEM = (
    "[task:intent]\n"
    "Classify the customer's last message into exactly one intent "
    "(order, browse, reserve, track, pay, support, smalltalk, escalate) and "
    "detect the language (ar-EG or en). Return only the structured object."
)


async def intent_node(state: ConvState) -> dict[str, Any]:
    iid = state.inbound.interactive_id
    if iid:
        if iid.startswith("add::"):
            return {"intent": Intent.ORDER, "lang": state.lang}
        if iid in _BUTTON_INTENT:
            return {"intent": _BUTTON_INTENT[iid], "lang": state.lang}

    text = state.text_norm or state.inbound.text
    try:
        out = await get_llm().structured(
            system=_SYSTEM,
            messages=[{"role": "user", "content": text}],
            model=settings.intent_model,
            schema=_SCHEMA,
        )
        return {"intent": Intent(out["intent"]), "lang": Lang(out["lang"])}
    except Exception:
        return {"intent": guess_intent(text), "lang": detect_lang(text)}
