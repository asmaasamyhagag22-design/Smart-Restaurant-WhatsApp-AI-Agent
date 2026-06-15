"""End-to-end smoke test of the local agent (no server, no API keys)."""
import asyncio

from app.config import settings
from app.deps import get_repos
from app.schemas.enums import MessageType
from app.schemas.messaging import InboundMessage
from app.seed.seed_demo import seed_if_empty
from app.services.pipeline import process_inbound


async def turn(text=None, iid=None, frm="+20100000001"):
    repos = get_repos()
    tenant = await repos.tenants.get_by_slug(settings.default_tenant_slug)
    msg = InboundMessage(
        tenant_id=tenant.id,
        channel="local",
        from_phone=frm,
        type=MessageType.INTERACTIVE if iid else MessageType.TEXT,
        text=text or "",
        interactive_id=iid,
    )
    out = await process_inbound(msg)
    print("=" * 64)
    print("IN :", iid or text)
    print("OUT:", out.text)
    if out.buttons:
        print("BTN:", [f"{b.id}={b.title}" for b in out.buttons])
    for s in out.list_sections:
        print("LIST:", [r.id for r in s.rows][:6])
    print("meta:", out.meta)
    return out


async def main():
    await seed_if_empty()
    await turn("عايز شاورما فراخ")
    await turn(iid="confirm_order")
    await turn(iid="pay_cod")
    await turn("فين الأوردر؟")
    await turn("المنيو")
    await turn(iid="add::FRIES-L")
    await turn(iid="confirm_order")
    await turn(iid="pay_card")
    await turn("احجز ترابيزة ٤ افراد بكرة الساعة ٨")
    await turn("عايزة اكلم حد من خدمة العملاء")
    print("\nSMOKE OK")


if __name__ == "__main__":
    asyncio.run(main())
