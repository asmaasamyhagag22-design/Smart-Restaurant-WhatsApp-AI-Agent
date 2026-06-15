"""In-memory vector store with Pinecone-style metadata filtering.

Default for local development. Implements the same operator filter language
(``$lte``, ``$gte``, ``$in``, ``$nin``, ``$eq``, ``$exists``) used by the menu
RAG tool, so swapping in pgvector/Pinecone needs no caller changes.
"""
from __future__ import annotations

import math
from typing import Any

from app.providers.base import BaseVectorStore, VectorHit, VectorRecord


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


def _match_filter(meta: dict[str, Any], flt: dict[str, Any] | None) -> bool:
    if not flt:
        return True
    for key, cond in flt.items():
        val = meta.get(key)
        if isinstance(cond, dict):
            for op, operand in cond.items():
                if op == "$eq" and val != operand:
                    return False
                if op == "$lte" and not (val is not None and val <= operand):
                    return False
                if op == "$gte" and not (val is not None and val >= operand):
                    return False
                if op == "$exists" and (val is not None) != bool(operand):
                    return False
                if op == "$in":
                    vals = val if isinstance(val, list) else [val]
                    if not any(v in operand for v in vals):
                        return False
                if op == "$nin":
                    vals = val if isinstance(val, list) else [val]
                    if any(v in operand for v in vals):
                        return False
        else:
            if val != cond:
                return False
    return True


class MemoryVectorStore(BaseVectorStore):
    def __init__(self) -> None:
        # namespace -> {id: (vector, metadata)}
        self._ns: dict[str, dict[str, tuple[list[float], dict[str, Any]]]] = {}

    async def upsert(self, namespace: str, records: list[VectorRecord]) -> None:
        ns = self._ns.setdefault(namespace, {})
        for r in records:
            ns[r.id] = (r.values, r.metadata)

    async def query(
        self,
        namespace: str,
        vector: list[float],
        top_k: int = 5,
        flt: dict[str, Any] | None = None,
    ) -> list[VectorHit]:
        ns = self._ns.get(namespace, {})
        scored: list[VectorHit] = []
        for vid, (vec, meta) in ns.items():
            if not _match_filter(meta, flt):
                continue
            scored.append(VectorHit(id=vid, score=_cosine(vector, vec), metadata=meta))
        scored.sort(key=lambda h: h.score, reverse=True)
        return scored[:top_k]

    async def delete(self, namespace: str, ids: list[str] | None = None) -> None:
        if ids is None:
            self._ns.pop(namespace, None)
            return
        ns = self._ns.get(namespace, {})
        for i in ids:
            ns.pop(i, None)
