"""respond node — compose the WhatsApp-shaped reply.

Replies are built deterministically from cart + tool results so prices are never
hallucinated (docs §10). Natural prose for smalltalk/support goes through the LLM
(mock or Claude). Button/list ids round-trip back through the intent/plan nodes.
"""
from __future__ import annotations

from typing import Any

from app.agent.state import ConvState
from app.config import settings
from app.deps import get_llm
from app.schemas.domain import format_money
from app.schemas.enums import Intent, Lang
from app.schemas.messaging import Button, ListRow, ListSection, OutboundMessage


def _cart_message(state: ConvState, to: str, lang: Lang, meta: dict) -> OutboundMessage:
    ar = lang == Lang.AR
    lines = [
        f"• {i.qty}× {i.display_name(lang)} — {format_money(i.line_total_cents, lang)}"
        for i in state.cart.items
    ]
    total = format_money(state.cart.total_cents, lang)
    body = "\n".join(lines)
    if ar:
        text = f"السلة 🛒\n{body}\n────────────\nالإجمالي: {total}"
        buttons = [
            Button(id="confirm_order", title="تأكيد الأوردر"),
            Button(id="add_more", title="أضيف حاجة"),
            Button(id="cancel_order", title="إلغاء"),
        ]
    else:
        text = f"Your cart 🛒\n{body}\n────────────\nTotal: {total}"
        buttons = [
            Button(id="confirm_order", title="Confirm"),
            Button(id="add_more", title="Add more"),
            Button(id="cancel_order", title="Cancel"),
        ]
    return OutboundMessage(to=to, text=text, rtl=ar, buttons=buttons, meta=meta)


def _menu_list_message(
    matches: list[dict], to: str, lang: Lang, meta: dict, header: str | None = None
) -> OutboundMessage:
    ar = lang == Lang.AR
    rows = [
        ListRow(
            id=f"add::{m['sku']}",
            title=((m["name_ar"] if ar else m["name_en"]) or m["sku"])[:24],
            description=format_money(m["price_cents"], lang),
        )
        for m in matches[:10]
    ]
    title = header or ("المنيو" if ar else "Menu")
    text = header or ("اختار من المنيو 👇" if ar else "Pick from the menu 👇")
    return OutboundMessage(
        to=to,
        text=text,
        rtl=ar,
        list_button_text=("اعرض" if ar else "View"),
        list_sections=[ListSection(title=title[:24], rows=rows)],
        meta=meta,
    )


def _payment_options_message(state: ConvState, to: str, lang: Lang, meta: dict) -> OutboundMessage:
    ar = lang == Lang.AR
    total = format_money(state.cart.total_cents, lang)
    if ar:
        text = f"تمام ✅ الإجمالي {total}. تحب تدفع إزاي؟"
        buttons = [
            Button(id="pay_card", title="فيزا/كارت 💳"),
            Button(id="pay_cod", title="كاش عند الاستلام"),
        ]
    else:
        text = f"Great ✅ Total {total}. How would you like to pay?"
        buttons = [
            Button(id="pay_card", title="Card 💳"),
            Button(id="pay_cod", title="Cash on delivery"),
        ]
    return OutboundMessage(to=to, text=text, rtl=ar, buttons=buttons, meta=meta)


async def respond_node(state: ConvState) -> dict[str, Any]:
    lang = state.lang
    ar = lang == Lang.AR
    to = state.inbound.from_phone
    tr = state.tool_results
    iid = state.inbound.interactive_id
    meta = {"tools": list(tr.keys()), "intent": state.intent.value if state.intent else None}

    def out(msg: OutboundMessage) -> dict[str, Any]:
        return {"outbound": msg}

    # ── escalation ────────────────────────────────────────────────────
    if state.escalate:
        text = (
            "تمام، بحوّلك لزميل من خدمة العملاء حالاً 🙋 استنى لحظة."
            if ar
            else "Sure — connecting you to a human agent now 🙋 One moment."
        )
        return {"outbound": OutboundMessage(to=to, text=text, rtl=ar, meta=meta), "escalate": True}

    # ── add-more prompt ───────────────────────────────────────────────
    if iid == "add_more":
        text = "تحب تضيف إيه؟ اكتبلي اسم الأكل 😋" if ar else "What would you like to add? Type the item 😋"
        return out(OutboundMessage(to=to, text=text, rtl=ar, meta=meta))

    # ── payment result ────────────────────────────────────────────────
    if "create_payment" in tr:
        r = tr["create_payment"]
        if r.get("payment_url"):
            text = (
                f"تمام! ده لينك الدفع الآمن 💳\nالإجمالي: {format_money(r['total_cents'], lang)}\n{r['payment_url']}"
                if ar
                else f"Here's your secure payment link 💳\nTotal: {format_money(r['total_cents'], Lang.EN)}\n{r['payment_url']}"
            )
        else:
            oid = str(r.get("order_id", ""))[:8]
            text = (
                f"اتسجّل أوردرك ✅ هيتدفع كاش عند الاستلام.\nرقم الأوردر: {oid}\nالإجمالي: {format_money(r['total_cents'], lang)}"
                if ar
                else f"Order placed ✅ Cash on delivery.\nOrder #{oid}\nTotal: {format_money(r['total_cents'], Lang.EN)}"
            )
        return out(OutboundMessage(to=to, text=text, rtl=ar, meta=meta))

    # ── tracking ──────────────────────────────────────────────────────
    if "track_order" in tr:
        r = tr["track_order"]
        if not r.get("found"):
            text = "مفيش أوردر شغّال ليك دلوقتي 🤔 تحب تطلب حاجة؟" if ar else "No active order found 🤔 Want to place one?"
        else:
            oid = str(r["order_id"])[:8]
            text = (
                f"أوردرك #{oid} حالته: {r['status']} ⏱️ تقريباً {r.get('eta_minutes', 30)} دقيقة"
                if ar
                else f"Order #{oid} — status: {r['status']} ⏱️ ~{r.get('eta_minutes', 30)} min"
            )
        return out(OutboundMessage(to=to, text=text, rtl=ar, meta=meta))

    # ── reservation ───────────────────────────────────────────────────
    if "book_table" in tr:
        r = tr["book_table"]
        if r.get("available"):
            text = (
                f"تم الحجز ✅ {r['party_size']} أفراد · {r['slot']} · {r['area']}. مستنينك! 🎉"
                if ar
                else f"Booked ✅ {r['party_size']} guests · {r['slot']} · {r['area']}. See you! 🎉"
            )
        else:
            text = "الميعاد ده محجوز بالكامل 😕 تحب ميعاد تاني؟" if ar else "That slot is full 😕 Try another time?"
        return out(OutboundMessage(to=to, text=text, rtl=ar, meta=meta))

    # ── confirm / pay (typed or button) ───────────────────────────────
    if iid == "confirm_order" or state.intent == Intent.PAY:
        if state.cart.is_empty:
            text = "سلتك فاضية 🛒 اطلب الأول وبعدين ندفع." if ar else "Your cart is empty 🛒 Order something first."
            return out(OutboundMessage(to=to, text=text, rtl=ar, meta=meta))
        return out(_payment_options_message(state, to, lang, meta))

    # ── multi-item order added ────────────────────────────────────────
    if "order_items" in tr:
        r = tr["order_items"]
        notfound = r.get("notfound") or []
        if state.cart.is_empty:
            base = "ملقتش الأصناف دي 😅 جرّب تكتب اسم الأكل تاني أو اطلب «المنيو»." if ar \
                else "Couldn't find those items 😅 try again or ask for the menu."
            return out(OutboundMessage(to=to, text=base, rtl=ar, meta=meta))
        msg = _cart_message(state, to, lang, meta)
        if notfound:
            msg.text += (
                "\n\n(ملقتش: " + "، ".join(notfound) + ")"
                if ar
                else "\n\n(not found: " + ", ".join(notfound) + ")"
            )
        return out(msg)

    # ── cart updated (single tap/edit) ────────────────────────────────
    if "update_cart" in tr:
        if state.cart.is_empty:
            text = "السلة فاضية دلوقتي 🛒" if ar else "Your cart is now empty 🛒"
            return out(OutboundMessage(to=to, text=text, rtl=ar, meta=meta))
        return out(_cart_message(state, to, lang, meta))

    # ── menu search ───────────────────────────────────────────────────
    if "query_menu" in tr:
        matches = tr["query_menu"].get("matches", [])
        if not matches:
            text = "ملقتش حاجة بالظبط كده 😅 ممكن توصفلي تاني؟" if ar else "I couldn't find that 😅 Could you rephrase?"
            return out(OutboundMessage(to=to, text=text, rtl=ar, meta=meta))
        return out(_menu_list_message(matches, to, lang, meta))

    # ── recommendations ───────────────────────────────────────────────
    if "recommend" in tr:
        matches = tr["recommend"].get("matches", [])
        header = "اقترحلك دول 👇" if ar else "Picks for you 👇"
        return out(_menu_list_message(matches, to, lang, meta, header=header))

    # ── smalltalk / fallback (LLM prose) ──────────────────────────────
    if ar:
        system = (
            "[task:respond]\n"
            "إنت مساعد مطعم بطة على واتساب. ردّك بالعامية المصرية، قصير جداً وودود "
            "(سطر أو اتنين)، ووجّه العميل إنه يطلب أكل أو يشوف المنيو. "
            "ممنوع تخترع أصناف أو أسعار من عندك."
        )
    else:
        system = (
            "[task:respond]\n"
            "You are Batta restaurant's WhatsApp assistant. Reply in short, friendly "
            "English (one or two lines) and steer the customer to order or view the menu. "
            "Never invent menu items or prices."
        )
    res = await get_llm().complete(
        system=system,
        messages=[{"role": "user", "content": state.text_norm or state.inbound.text}],
        model=settings.reflect_model,
        temperature=0.5,
    )
    buttons = [Button(id="show_menu", title="اعرض المنيو" if ar else "View menu")]
    return out(OutboundMessage(to=to, text=res.text or "", rtl=ar, buttons=buttons, meta=meta))
