from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth
from app.core.config import settings
from app.core.errors import register_error_handlers
from app.core.logging import RequestIdMiddleware, configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging(settings.app_env)
    yield
    # Sin tareas de apagado: no hay scheduler ni proceso de fondo que detener
    # (turnos y reservas se resuelven bajo demanda, ver 02_Documento_Tecnico.md §10).


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    register_error_handlers(app)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get(f"{settings.api_prefix}/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "env": settings.app_env}

    app.include_router(auth.router, prefix=settings.api_prefix)

    return app


app = create_app()
