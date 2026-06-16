"""Dependency factory — selects the concrete provider/repository implementation
from settings. Imports are lazy so importing this module never fails because an
optional backend (or a not-yet-built module) is missing. Each accessor is a
cached singleton for the process lifetime.
"""
from __future__ import annotations

from functools import lru_cache

from app.config import settings
from app.logging_conf import get_logger
from app.providers.base import (
    BaseChannel,
    BaseEmbedder,
    BaseLLM,
    BasePSP,
    BaseSTT,
    BaseVectorStore,
    BaseVision,
)
from app.repositories.base import Repos

log = get_logger("deps")


@lru_cache
def get_llm() -> BaseLLM:
    provider = settings.llm_provider
    if provider == "gemini":
        if not (settings.gcp_project or settings.google_api_key):
            log.error("llm_provider=gemini but neither GCP_PROJECT nor GOOGLE_API_KEY set; using mock")
        else:
            try:
                from app.providers.llm_gemini import GeminiLLM

                return GeminiLLM()
            except Exception as e:  # missing google-genai / bad creds
                log.error("gemini_llm_init_failed; using mock", error=str(e)[:200])
    elif provider == "vertex":
        if not settings.gcp_project:
            log.error("llm_provider=vertex but GCP_PROJECT is missing; using mock")
        else:
            try:
                from app.providers.llm_anthropic import VertexLLM

                return VertexLLM()
            except Exception as e:  # missing anthropic[vertex] / bad ADC
                log.error("vertex_llm_init_failed; using mock", error=str(e)[:200])
    elif provider == "anthropic":
        if not settings.anthropic_api_key:
            log.error("llm_provider=anthropic but ANTHROPIC_API_KEY missing; using mock")
        else:
            try:
                from app.providers.llm_anthropic import AnthropicLLM

                return AnthropicLLM()
            except Exception as e:
                log.error("anthropic_llm_init_failed; using mock", error=str(e)[:200])

    from app.providers.llm_mock import MockLLM

    return MockLLM()


@lru_cache
def get_embedder() -> BaseEmbedder:
    p = settings.embed_provider
    if p == "fastembed":
        try:
            from app.providers.embeddings import FastEmbedEmbedder

            return FastEmbedEmbedder()
        except Exception as e:  # missing model / offline — degrade gracefully
            log.warning("fastembed unavailable, falling back to hash", error=str(e)[:120])
    if p == "openai" and settings.openai_api_key:
        from app.providers.embeddings import OpenAIEmbedder

        return OpenAIEmbedder()
    from app.providers.embeddings import HashEmbedder

    return HashEmbedder()


@lru_cache
def get_vector_store() -> BaseVectorStore:
    p = settings.vector_provider
    if p == "pgvector":
        from app.providers.vector_pgvector import PgVectorStore

        return PgVectorStore()
    if p == "pinecone":
        from app.providers.vector_pinecone import PineconeStore

        return PineconeStore()
    from app.providers.vector_memory import MemoryVectorStore

    return MemoryVectorStore()


@lru_cache
def get_channel() -> BaseChannel:
    if settings.channel_provider == "whatsapp":
        from app.providers.channel_whatsapp import WhatsAppChannel

        return WhatsAppChannel()
    from app.providers.channel_local import LocalChannel

    return LocalChannel()


@lru_cache
def get_psp() -> BasePSP:
    p = settings.psp_provider
    if p == "paymob":
        from app.providers.psp_paymob import PaymobPSP

        return PaymobPSP()
    if p == "stripe":
        from app.providers.psp_stripe import StripePSP

        return StripePSP()
    from app.providers.psp_mock import MockPSP

    return MockPSP()


@lru_cache
def get_stt() -> BaseSTT:
    p = settings.stt_provider
    if p == "whisper_local":
        try:
            from app.providers.stt import WhisperLocalSTT

            return WhisperLocalSTT()
        except Exception as e:
            log.warning("whisper_local unavailable, using mock", error=str(e)[:120])
    if p == "openai" and settings.openai_api_key:
        from app.providers.stt import OpenAISTT

        return OpenAISTT()
    from app.providers.stt import MockSTT

    return MockSTT()


@lru_cache
def get_vision() -> BaseVision:
    if settings.vision_provider == "anthropic" and settings.anthropic_api_key:
        from app.providers.vision import AnthropicVision

        return AnthropicVision()
    from app.providers.vision import MockVision

    return MockVision()


@lru_cache
def get_repos() -> Repos:
    if settings.store_backend == "sql":
        from app.repositories.sql import build_sql_repos

        return build_sql_repos()
    from app.repositories.memory import build_memory_repos

    return build_memory_repos()
