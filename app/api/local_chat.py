"""Local WhatsApp simulator: serves the chat UI and a synchronous /chat endpoint,
plus a mock payment confirmation page. This is the local stand-in for the Meta
Cloud API channel."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from app.config import settings
from app.deps import get_channel, get_repos
from app.schemas.enums import OrderStatus, PaymentStatus
from app.services.pipeline import process_inbound

router = APIRouter(tags=["local"])

_WEB = Path(__file__).resolve().parents[2] / "web" / "chat.html"


@router.get("/", response_class=HTMLResponse)
async def home() -> str:
    if _WEB.exists():
        return _WEB.read_text(encoding="utf-8")
    return "<h1>Smart Restaurant Agent</h1><p>chat UI missing</p>"


@router.post("/chat")
async def chat(req: Request) -> JSONResponse:
    body = await req.json()
    repos = get_repos()
    tenant = await repos.tenants.get_by_slug(settings.default_tenant_slug)
    tenant_id = tenant.id if tenant else settings.default_tenant_slug
    inbound = get_channel().parse_inbound(body, tenant_id)[0]
    out = await process_inbound(inbound)
    return JSONResponse(out.model_dump())


@router.get("/pay/mock/{reference}", response_class=HTMLResponse)
async def mock_pay(reference: str) -> str:
    repos = get_repos()
    order = await repos.orders.get_by_reference(reference)
    if order:
        await repos.orders.update_status(
            order.id, status=OrderStatus.CONFIRMED, payment_status=PaymentStatus.PAID
        )
        body = "✅ تم الدفع بنجاح (mock)<br>تقدر ترجع للشات."
    else:
        body = "⚠️ الطلب مش موجود."
    return (
        "<html dir='rtl'><body style='font-family:sans-serif;background:#0A0D12;"
        "color:#E8ECF1;display:grid;place-items:center;height:100vh'>"
        f"<div style='text-align:center'><h2>{body}</h2></div></body></html>"
    )
