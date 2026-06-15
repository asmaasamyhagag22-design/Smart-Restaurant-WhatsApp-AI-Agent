"""Speech-to-text providers (mock + local Whisper + OpenAI)."""
from __future__ import annotations

import asyncio

from app.config import settings
from app.providers.base import BaseSTT


class MockSTT(BaseSTT):
    async def transcribe(self, audio: bytes, lang_hint: str = "ar") -> str:
        # Deterministic sample mirroring the docs voice-note flow.
        return "عايز اتنين شاورما فراخ، واحد بدون طرشي، ومعاهم بطاطس وكولا"


class WhisperLocalSTT(BaseSTT):
    """faster-whisper (CPU). Optional heavy dependency, imported lazily."""

    def __init__(self) -> None:
        from faster_whisper import WhisperModel

        self._model = WhisperModel("large-v3", device="cpu", compute_type="int8")

    async def transcribe(self, audio: bytes, lang_hint: str = "ar") -> str:
        import os
        import tempfile

        def _run() -> str:
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
                f.write(audio)
                path = f.name
            try:
                segments, _ = self._model.transcribe(path, language=lang_hint)
                return " ".join(s.text for s in segments).strip()
            finally:
                os.unlink(path)

        return await asyncio.to_thread(_run)


class OpenAISTT(BaseSTT):
    def __init__(self) -> None:
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def transcribe(self, audio: bytes, lang_hint: str = "ar") -> str:
        import io

        bio = io.BytesIO(audio)
        bio.name = "audio.ogg"
        resp = await self._client.audio.transcriptions.create(
            model="whisper-1", file=bio, language=lang_hint
        )
        return resp.text
