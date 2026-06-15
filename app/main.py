"""FastAPI application factory.

Local default boots fully self-contained: in-memory store, mock LLM, local
channel, demo menu seeded at startup. Production routers (webhooks/admin) are
included when present.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.logging_conf import configure_logging, get_logger

log = get_logger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    if settings.store_backend == "memory":
        from app.seed.seed_demo import seed_if_empty

        await seed_if_empty()
    log.info(
        "startup_complete",
        env=settings.env,
        llm=settings.llm_provider,
        store=settings.store_backend,
        vector=settings.vector_provider,
        channel=settings.channel_provider,
    )
    yield


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="1.2.0", lifespan=lifespan)

    from app.api.health import router as health_router
    from app.api.local_chat import router as local_router

    app.include_router(health_router)
    app.include_router(local_router)

    # production routers (added in stage 2); optional so local always boots
    try:
        from app.api.webhooks import router as webhooks_router

        app.include_router(webhooks_router)
    except Exception as e:  # pragma: no cover
        log.info("webhooks_router_skipped", reason=str(e)[:80])
    try:
        from app.api.admin import router as admin_router

        app.include_router(admin_router)
    except Exception as e:  # pragma: no cover
        log.info("admin_router_skipped", reason=str(e)[:80])

    return app


app = create_app()
