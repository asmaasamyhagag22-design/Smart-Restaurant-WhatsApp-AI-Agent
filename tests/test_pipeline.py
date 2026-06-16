"""End-to-end conversation flows through the agent graph (mock LLM, in-memory)."""


async def test_single_item_order(say):
    out = await say("عايز شاورما فراخ", frm="+2010001")
    assert "شاورما فراخ" in out.text
    assert "85" in out.text
    assert {b.id for b in out.buttons} >= {"confirm_order", "cancel_order"}


async def test_bare_dish_name_orders(say):
    # typing just the dish name (no "عايز") should add it to the cart
    out = await say("شاورما فراخ", frm="+2010021")
    assert "شاورما فراخ" in out.text
    assert "85" in out.text


async def test_multi_item_order(say):
    out = await say("عايز برجر لحمة وبطاطس وكوكا", frm="+2010002")
    assert "برجر" in out.text and "بطاطس" in out.text
    # 110 + 35 + 15 = 160
    assert "160" in out.text


async def test_modifier_order(say):
    out = await say("عايز برجر لحمة بدون مخلل", frm="+2010003")
    assert "بدون مخلل" in out.text


async def test_pay_flow_cod(say):
    await say("عايز شاورما فراخ", frm="+2010004")
    opts = await say(iid="confirm_order", frm="+2010004")
    assert {b.id for b in opts.buttons} == {"pay_card", "pay_cod"}
    done = await say(iid="pay_cod", frm="+2010004")
    assert "كاش" in done.text or "أوردر" in done.text


async def test_track_after_order(say):
    await say("عايز برجر فراخ", frm="+2010005")
    await say(iid="confirm_order", frm="+2010005")
    await say(iid="pay_cod", frm="+2010005")
    out = await say("فين الأوردر؟", frm="+2010005")
    assert "حالته" in out.text


async def test_reservation(say):
    out = await say("احجز ترابيزة ٤ افراد بكرة الساعة ٨", frm="+2010006")
    assert "الحجز" in out.text


async def test_escalation(say):
    out = await say("عايزة اكلم حد من خدمة العملاء", frm="+2010007")
    assert out.meta.get("intent") == "support"
    assert "خدمة العملاء" in out.text or "زميل" in out.text


async def test_english_order(say):
    out = await say("I want a beef burger", frm="+2010008")
    assert not out.rtl
    assert "Burger" in out.text and "EGP" in out.text


async def test_menu_browse_list(say):
    out = await say("المنيو", frm="+2010009")
    assert out.list_sections
    assert out.list_sections[0].rows
