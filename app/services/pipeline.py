"""Inbound pipeline — the spine that turns a raw message into a reply.

resolve tenant/customer → rehydrate conversation → multimodal pre-process →
security (sanitize + PII redact + Arabizi normalize) → run the LangGraph agent →
persist state → restore PII → dispatch.
"""
from __future__ import annotations

import httpx

from app.agent.graph import get_agent
from app.agent.state import ConvState, CustomerCtx, Turn
from app.config import settings
from app.deps import get_channel, get_repos, get_stt, get_vision
from app.logging_conf import get_logger
from app.schemas.domain import Cart
from app.schemas.enums import ConversationStatus, Lang, MessageType
from app.schemas.messaging import InboundMessage, OutboundMessage
from app.security import injection, pii
from app.services import telemetry
from app.services.text import normalize_arabizi

log = get_logger("pipeline")

_LANGS = {l.value for l in Lang}


async def _fetch_media(inbound: InboundMessage) -> bytes | None:
    if not inbound.media_url:
        return None
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(inbound.media_url)
            r.raise_for_status()
            return r.content
    except Exception as e:
        log.warning("media_fetch_failed", error=str(e)[:120])
        return None


async def _to_text(inbound: InboundMessage) -> str:
    """Collapse any modality into a text request for the agent."""
    if inbound.type == MessageType.AUDIO:
        audio = await _fetch_media(inbound)
        return await get_stt().transcribe(audio) if audio else inbound.text
    if inbound.type == MessageType.IMAGE:
        image = await _fetch_media(inbound)
        if image:
            items = await get_vision().extract_menu(image)
            if items:
                first = items[0]
                return first.get("name_ar") or first.get("name_en") or inbound.text
        return inbound.text
    if inbound.type == MessageType.LOCATION:
        return f"📍 {inbound.latitude},{inbound.longitude}"
    return inbound.text


async def process_inbound(inbound: InboundMessage) -> OutboundMessage:
    repos = get_repos()
    tenant = await repos.tenants.get(inbound.tenant_id)
    if tenant is None:
        tenant = await repos.tenants.get_by_slug(settings.default_tenant_slug)
    if tenant is None:
        return OutboundMessage(to=inbound.from_phone, text="Service unavailable.", rtl=False)

    inbound.tenant_id = tenant.id
    customer = await repos.customers.get_or_create(tenant.id, inbound.from_phone)
    conv = await repos.conversations.get_active(tenant.id, customer.id)
    if conv is None:
        conv = await repos.conversations.create(tenant.id, customer.id)

    # rehydrate durable conversation memory
    saved = conv.state or {}
    cart = Cart(**saved["cart"]) if saved.get("cart") else Cart()
    history = [Turn(**t) for t in saved.get("history", [])][-10:]
    summary = saved.get("summary", "")

    raw_text = inbound.text
    text = await _to_text(inbound)
    inbound.text = text

    # security pre-hooks
    text = injection.sanitize(text)
    redacted, pii_map = pii.redact(text)
    norm = normalize_arabizi(redacted)

    lang = Lang(customer.preferred_lang) if customer.preferred_lang in _LANGS else settings.default_lang

    recent = await repos.orders.recent_for_customer(tenant.id, customer.id, 3)
    state = ConvState(
        tenant_id=tenant.id,
        conversation_id=conv.id,
        customer=CustomerCtx(
            id=customer.id,
            phone=customer.phone,
            name=customer.name,
            preferred_lang=lang,
            diet_tags=customer.diet_tags,
            zone=customer.zone,
            recent_orders=[{"items": o.items, "total_cents": o.total_cents} for o in recent],
        ),
        lang=lang,
        inbound=inbound,
        text_norm=norm,
        cart=cart,
        history=history,
        summary=summary,
        pii_map=pii_map,
    )

    try:
        result = await get_agent().ainvoke(state)
        final = result if isinstance(result, ConvState) else ConvState(**result)
    except Exception as e:
        log.error("agent_failed", error=str(e))
        msg = "حصلت مشكلة بسيطة 🙏 ممكن تجرّب تاني؟" if lang == Lang.AR else "Something went wrong 🙏 please retry."
        return OutboundMessage(to=inbound.from_phone, text=msg, rtl=lang == Lang.AR)

    outbound = final.outbound or OutboundMessage(
        to=inbound.from_phone, text="…", rtl=lang == Lang.AR
    )
    outbound.text = pii.restore(outbound.text, pii_map)

    # persist conversation memory
    new_history = history + [
        Turn(role="user", content=raw_text[:500]),
        Turn(role="assistant", content=outbound.text[:500]),
    ]
    status = ConversationStatus.ESCALATED if final.escalate else ConversationStatus.ACTIVE
    await repos.conversations.save_state(
        conv.id,
        {
            "cart": final.cart.model_dump(),
            "history": [t.model_dump(mode="json") for t in new_history[-10:]],
            "summary": summary,
        },
        status,
    )

    if final.lang.value != customer.preferred_lang:
        customer.preferred_lang = final.lang.value
        await repos.customers.update(customer)

    telemetry.record_turn(final.intent.value if final.intent else None, final.escalate)

    try:
        await get_channel().send(outbound)
    except Exception as e:
        log.warning("channel_send_failed", error=str(e)[:120])

    return outbound
