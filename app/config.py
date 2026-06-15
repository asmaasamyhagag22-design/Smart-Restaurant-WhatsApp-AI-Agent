"""Central application settings.

Every external dependency is selected by a ``*_provider`` / ``*_backend`` field so
the same code runs fully local (mock/in-memory, zero paid APIs) or in production
(Anthropic, Postgres+pgvector, Meta WhatsApp, real PSPs) by editing ``.env`` only.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── App ───────────────────────────────────────────────────────────
    app_name: str = "Smart Restaurant Agent"
    env: Literal["local", "staging", "production"] = "local"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8080
    # Public URL the outside world (PSP, Meta) uses to reach us; used for links.
    public_base_url: str = "http://localhost:8080"

    # ── Provider selection ────────────────────────────────────────────
    store_backend: Literal["memory", "sql"] = "memory"
    llm_provider: Literal["anthropic", "mock"] = "mock"
    vector_provider: Literal["memory", "pgvector", "pinecone"] = "memory"
    channel_provider: Literal["local", "whatsapp"] = "local"
    psp_provider: Literal["mock", "paymob", "stripe"] = "mock"
    stt_provider: Literal["mock", "whisper_local", "openai"] = "mock"
    vision_provider: Literal["mock", "anthropic"] = "mock"
    embed_provider: Literal["fastembed", "hash", "openai"] = "fastembed"

    # ── LLM (Anthropic) ───────────────────────────────────────────────
    anthropic_api_key: str | None = None
    # Optional OpenAI key (only for embed_provider=openai / stt_provider=openai)
    openai_api_key: str | None = None
    intent_model: str = "claude-haiku-4-5-20251001"
    plan_model: str = "claude-sonnet-4-6"
    reflect_model: str = "claude-sonnet-4-6"
    vision_model: str = "claude-sonnet-4-6"
    llm_max_tokens: int = 1024
    llm_temperature: float = 0.2

    # ── Embeddings ────────────────────────────────────────────────────
    embed_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embed_dim: int = 384

    # ── Database (used when store_backend="sql") ──────────────────────
    database_url: str = "postgresql+asyncpg://restaurant:restaurant@localhost:5432/restaurant"
    db_echo: bool = False

    # ── Redis (optional cache/session; falls back to memory) ──────────
    redis_url: str | None = None

    # ── Celery (local default: run tasks inline) ──────────────────────
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    celery_task_always_eager: bool = True

    # ── WhatsApp (Meta Cloud API) — production channel ────────────────
    wa_verify_token: str = "dev-verify-token"
    wa_app_secret: str | None = None
    wa_access_token: str | None = None
    wa_phone_number_id: str | None = None
    wa_api_version: str = "v17.0"

    # ── Payment service providers ─────────────────────────────────────
    paymob_api_key: str | None = None
    paymob_hmac_secret: str | None = None
    stripe_api_key: str | None = None
    stripe_webhook_secret: str | None = None

    # ── Agent behaviour ───────────────────────────────────────────────
    max_hops: int = 8
    history_summary_after: int = 6
    default_lang: Literal["ar-EG", "en"] = "ar-EG"

    # ── Observability ─────────────────────────────────────────────────
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str | None = None
    log_level: str = "INFO"
    log_json: bool = False

    # ── Security / multi-tenancy ──────────────────────────────────────
    admin_jwt_secret: str = "dev-admin-secret-change-me"
    default_tenant_slug: str = "zaffran"

    @property
    def is_local(self) -> bool:
        return self.env == "local"


@lru_cache
def get_settings() -> Settings:
    """Cached singleton settings instance."""
    return Settings()


settings = get_settings()
