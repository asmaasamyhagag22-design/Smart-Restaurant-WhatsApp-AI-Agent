"""Seed the demo tenant + menu and index it into the vector store."""
from __future__ import annotations

import json
from pathlib import Path

from app.config import settings
from app.deps import get_embedder, get_repos, get_vector_store
from app.logging_conf import get_logger
from app.providers.base import VectorRecord
from app.repositories.base import Repos
from app.schemas.entities import MenuItemRecord, TenantRecord

log = get_logger("seed")
MENU_FILE = Path(__file__).with_name("demo_menu.json")


def _menu_metadata(it: MenuItemRecord) -> dict:
    return {
        "item_id": it.id,
        "sku": it.sku,
        "name_ar": it.name_ar,
        "name_en": it.name_en,
        "description": it.description,
        "price_cents": it.price_cents,
        "allergens": it.allergens,
        "diet": it.diet_tags,
        "spice": it.spice_level,
        "in_stock": it.in_stock,
    }


async def _index_menu(repos: Repos, tenant: TenantRecord) -> None:
    data = json.loads(MENU_FILE.read_text(encoding="utf-8"))
    items: list[MenuItemRecord] = []
    texts: list[str] = []
    for d in data:
        rec = await repos.menu.upsert(MenuItemRecord(id="", tenant_id=tenant.id, **d))
        items.append(rec)
        texts.append(
            f"{rec.name_ar} {rec.name_en} {rec.description} "
            f"{' '.join(rec.diet_tags)} {rec.category}"
        )

    embedder = get_embedder()
    store = get_vector_store()
    vectors = await embedder.embed_many(texts)
    records = [
        VectorRecord(id=it.id, values=vec, metadata=_menu_metadata(it))
        for it, vec in zip(items, vectors, strict=False)
    ]
    await store.upsert(tenant.id, records)
    log.info("menu_indexed", tenant=tenant.slug, items=len(items))


async def seed_if_empty() -> None:
    repos = get_repos()
    tenant = await repos.tenants.get_by_slug(settings.default_tenant_slug)
    if tenant is None:
        tenant = await repos.tenants.upsert(
            TenantRecord(
                id="",
                slug=settings.default_tenant_slug,
                name="مطعم زعفران",
                whatsapp_phone="+201000000000",
                persona_name="زعفران",
                voice_guidelines="ودود، مصري، مختصر، بيستخدم إيموجي بسيط",
                enabled_payments=["cod", "card"],
            )
        )
        log.info("tenant_seeded", slug=tenant.slug)
    await _index_menu(repos, tenant)
