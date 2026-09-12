"""Punto de entrada de la API de Morfi Center.

Levantar con:  ``uvicorn app.main:app --reload --port 8000``  (desde ``backend/``)
Docs:          http://localhost:8000/api/docs
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app import __version__
from app.api.routes import auth, health, users
from app.api.routes import settings as settings_routes
from app.core.config import settings
from app.core.errors import register_error_handlers
from app.core.logging import RequestContextMiddleware, configure_logging
from app.core.rate_limit import limiter, rate_limit_exceeded_handler

logger = logging.getLogger("morfi.app")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Ciclo de vida de la app. Preparado para arrancar/parar el scheduler."""
    logger.info("Morfi Center · arranque (env=%s, v%s)", settings.app_env, __version__)
    # TODO(T-2.3.1): iniciar APScheduler (jobs de turno y expiración de reservas)
    try:
        yield
    finally:
        # TODO(T-2.3.1): detener APScheduler
        logger.info("Morfi Center · apagado")


def create_app() -> FastAPI:
    configure_logging()

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        summary="Plataforma de pedidos anticipados de comida.",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # --- Rate limiting (slowapi) ---
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    # --- Middleware ---
    # Se agregan de adentro hacia afuera: el último es el más externo.
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["X-Request-Id"],
        )
    app.add_middleware(SlowAPIMiddleware)
    # RequestContextMiddleware queda como el más externo: asigna el request_id
    # antes que nada y cubre incluso las respuestas de error (incluido el 429).
    app.add_middleware(RequestContextMiddleware)

    # --- Handlers de error (formato único de la API) ---
    register_error_handlers(app)

    # --- Routers ---
    api = APIRouter(prefix=settings.api_prefix)
    api.include_router(health.router)
    api.include_router(auth.router)
    api.include_router(users.router)
    api.include_router(settings_routes.router)
    # A medida que avancen las fases se agregan aquí los routers de dominio
    # (catalog, orders, ...).
    app.include_router(api)

    return app


app = create_app()
