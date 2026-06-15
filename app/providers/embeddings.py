"""Embedding providers.

- ``FastEmbedEmbedder`` — local ONNX multilingual model (default, no torch).
- ``HashEmbedder``     — dependency-free deterministic fallback (offline).
- ``OpenAIEmbedder``   — text-embedding-3-* (production option).

E5-style models expect ``query:`` / ``passage:`` prefixes, so ``embed`` (query)
and ``embed_many`` (documents) add them automatically.
"""
from __future__ import annotations

import asyncio
import hashlib
import math

from app.config import settings
from app.providers.base import BaseEmbedder


class FastEmbedEmbedder(BaseEmbedder):
    def __init__(self) -> None:
        from fastembed import TextEmbedding  # imported lazily; may download a model

        self.dim = settings.embed_dim
        self._model = TextEmbedding(model_name=settings.embed_model)
        # E5 models expect query:/passage: prefixes; others don't.
        self._e5 = "e5" in settings.embed_model.lower()

    def _encode(self, texts: list[str]) -> list[list[float]]:
        return [list(map(float, v)) for v in self._model.embed(texts)]

    async def embed(self, text: str) -> list[float]:
        q = f"query: {text}" if self._e5 else text
        vecs = await asyncio.to_thread(self._encode, [q])
        return vecs[0]

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        docs = [f"passage: {t}" for t in texts] if self._e5 else texts
        return await asyncio.to_thread(self._encode, docs)


class HashEmbedder(BaseEmbedder):
    """Hashing-trick embedding over character 3-grams. Low semantic quality but
    deterministic and offline — keeps the demo running if fastembed is missing."""

    def __init__(self) -> None:
        self.dim = settings.embed_dim

    def _encode(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        t = text.lower().strip()
        grams = [t[i : i + 3] for i in range(max(1, len(t) - 2))] or [t]
        for g in grams:
            h = int(hashlib.md5(g.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dim
            sign = 1.0 if (h // self.dim) % 2 == 0 else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

    async def embed(self, text: str) -> list[float]:
        return self._encode(text)

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [self._encode(t) for t in texts]


class OpenAIEmbedder(BaseEmbedder):
    def __init__(self) -> None:
        from openai import AsyncOpenAI

        self.dim = settings.embed_dim
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = "text-embedding-3-large"

    async def embed(self, text: str) -> list[float]:
        return (await self.embed_many([text]))[0]

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        resp = await self._client.embeddings.create(
            model=self._model, input=texts, dimensions=self.dim
        )
        return [d.embedding for d in resp.data]
