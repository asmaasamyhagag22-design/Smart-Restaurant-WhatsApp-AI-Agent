"""Menu RAG (docs §06.2) — retrieve, never recite.

Hybrid retrieval: vector similarity + lexical overlap re-rank, validated against
live inventory. ``search_menu`` is the reusable core; ``query_menu`` is the
tool wrapper. ``check_allergens`` is mandatory for any allergy question.
"""
from __future__ import annotations

from typing import Any

from app.agent.state import ConvState
from app.deps import get_embedder, get_repos, get_vector_store
from app.schemas.domain import MenuQuery
from app.services.text import normalize_arabizi
from app.tools.base import ToolOutput, fail, ok

# words that carry no dish meaning — dropped before lexical matching
_STOP = {
    "عايز", "عاوز", "اطلب", "هات", "ضيف", "اضيف", "من", "في", "مع", "و", "ال",
    "want", "order", "add", "a", "an", "the", "get", "me", "some", "please", "i",
}


def _lexical(query: str, meta: dict[str, Any]) -> float:
    """Fraction of query tokens that appear (as substrings) in an item's text.

    Substring (not exact-token) match so partial words like ``كوكا`` hit
    ``كوكاكولا`` — this is the cheap re-rank signal that makes retrieval robust
    even when the embedding model is weak on Arabic.
    """
    q = [t for t in normalize_arabizi(query.lower()).split() if t not in _STOP and len(t) > 1]
    if not q:
        return 0.0
    text = normalize_arabizi(
        f"{meta.get('name_ar', '')} {meta.get('name_en', '')} {meta.get('description', '')}".lower()
    )
    return sum(1 for t in q if t in text) / len(q)


def _match_to_dict(meta: dict[str, Any], score: float) -> dict[str, Any]:
    return {
        "item_id": meta.get("item_id"),
        "sku": meta.get("sku"),
        "name_ar": meta.get("name_ar", ""),
        "name_en": meta.get("name_en", ""),
        "description": meta.get("description", ""),
        "price_cents": meta.get("price_cents", 0),
        "allergens": meta.get("allergens", []),
        "diet_tags": meta.get("diet", []),
        "spice_level": meta.get("spice", 0),
        "in_stock": meta.get("in_stock", True),
        "score": round(float(score), 4),
    }


async def _keyword_fallback(tenant_id: str, query: str, k: int) -> list[dict[str, Any]]:
    """Substring match if the vector index is empty / embeddings degraded."""
    repos = get_repos()
    items = await repos.menu.list(tenant_id)
    q = normalize_arabizi(query.lower())
    toks = {t for t in q.split() if t not in _STOP and len(t) > 1}
    scored: list[tuple[float, dict[str, Any]]] = []
    for it in items:
        if not it.in_stock:
            continue
        hay = normalize_arabizi(f"{it.name_ar} {it.name_en} {it.description}".lower())
        overlap = len({w for w in toks if w in hay})
        if toks and overlap == 0:
            continue
        meta = {
            "item_id": it.id, "sku": it.sku, "name_ar": it.name_ar, "name_en": it.name_en,
            "description": it.description, "price_cents": it.price_cents,
            "allergens": it.allergens, "diet": it.diet_tags, "spice": it.spice_level,
            "in_stock": it.in_stock,
        }
        scored.append((overlap or 0.1, _match_to_dict(meta, overlap)))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [m for _, m in scored[:k]]


async def search_menu(
    tenant_id: str,
    query: str,
    k: int = 5,
    diet: list[str] | None = None,
    exclude_allergens: list[str] | None = None,
    max_price_cents: int | None = None,
    spice_max: int = 3,
) -> list[dict[str, Any]]:
    """Reusable hybrid menu retrieval — used by query_menu and order_items."""
    embedder = get_embedder()
    store = get_vector_store()

    flt: dict[str, Any] = {"in_stock": {"$eq": True}, "spice": {"$lte": spice_max}}
    if diet:
        flt["diet"] = {"$in": diet}
    if exclude_allergens:
        flt["allergens"] = {"$nin": exclude_allergens}
    if max_price_cents:
        flt["price_cents"] = {"$lte": max_price_cents}

    matches: list[dict[str, Any]] = []
    try:
        vec = await embedder.embed(query)
        hits = await store.query(tenant_id, vec, top_k=max(k * 3, 12), flt=flt)
        ranked = sorted(
            hits,
            key=lambda h: _lexical(query, h.metadata) + 0.5 * float(h.score),
            reverse=True,
        )
        matches = [
            _match_to_dict(h.metadata, _lexical(query, h.metadata) + 0.5 * float(h.score))
            for h in ranked[:k]
        ]
    except Exception:
        matches = []

    if not matches:
        matches = await _keyword_fallback(tenant_id, query, k)
    return matches


async def query_menu(args: dict[str, Any], state: ConvState) -> ToolOutput:
    q = MenuQuery(
        query=args.get("query") or state.text_norm or "",
        diet=args.get("diet", []),
        exclude_allergens=args.get("exclude_allergens", []),
        max_price_cents=args.get("max_price_cents"),
        spice_max=int(args.get("spice_max", 3)),
        k=int(args.get("k", 5)),
    )
    matches = await search_menu(
        state.tenant_id, q.query, q.k, q.diet, q.exclude_allergens, q.max_price_cents, q.spice_max
    )
    return ok(matches=matches, query=q.query)


async def check_allergens(args: dict[str, Any], state: ConvState) -> ToolOutput:
    repos = get_repos()
    item = None
    if args.get("item_id"):
        item = await repos.menu.get(state.tenant_id, args["item_id"])
    if not item and args.get("sku"):
        item = await repos.menu.get_by_sku(state.tenant_id, args["sku"])
    if not item:
        return fail("item not found")
    return ok(
        sku=item.sku,
        name_ar=item.name_ar,
        name_en=item.name_en,
        allergens=item.allergens,
        has_allergens=bool(item.allergens),
    )
