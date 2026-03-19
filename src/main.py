"""FastAPI application entry point (HUB-002)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.adapters.telegram.adapter import TelegramAdapter
from src.api.routes import health, webhook
from src.config.settings import settings
from src.core.logger import get_logger, setup_logging
from src.core.registry import registry


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    setup_logging()
    log = get_logger(__name__)
    log.info("hub_starting", version=app.version, debug=settings.debug)

    registry.register(TelegramAdapter())
    log.info("adapters_ready", adapters=registry.list_all())

    yield
    log.info("hub_shutdown")


app = FastAPI(
    title="OneBox Integrations Hub",
    version="0.1.0",
    description="Centralized integration bus between CRM OneBox and external services.",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────
app.include_router(webhook.router, prefix="/api/v1")
app.include_router(health.router)
