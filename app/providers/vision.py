"""Vision providers — extract menu items/prices from a photo (mock + Claude)."""
from __future__ import annotations

import base64
import json
from typing import Any

from app.config import settings
from app.providers.base import BaseVision


class MockVision(BaseVision):
    async def extract_menu(self, image: bytes, prompt: str = "") -> list[dict[str, Any]]:
        return [
            {"name_en": "Lamb Mandi (large)", "name_ar": "مندي لحم (كبير)", "price_cents": 24000},
            {"name_en": "Chicken Shawarma", "name_ar": "شاورما فراخ", "price_cents": 8500},
        ]


class AnthropicVision(BaseVision):
    def __init__(self) -> None:
        from anthropic import AsyncAnthropic

        self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._model = settings.vision_model

    async def extract_menu(self, image: bytes, prompt: str = "") -> list[dict[str, Any]]:
        b64 = base64.standard_b64encode(image).decode()
        system = (
            "Extract every menu item and price from the image. "
            'Reply ONLY with a JSON array of {"name_en","name_ar","price_cents"}.'
        )
        msg = await self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=system,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {"type": "base64", "media_type": "image/jpeg", "data": b64},
                        },
                        {"type": "text", "text": prompt or "List the items and prices."},
                    ],
                }
            ],
        )
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        try:
            return json.loads(text)
        except Exception:
            return []
