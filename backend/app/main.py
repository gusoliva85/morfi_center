from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from starlette.middleware.sessions import SessionMiddleware

from app.api.routes import auth, shift, users
from app.api.routes import settings as settings_routes
from app.core.config import settings
from app.core.errors import register_error_handlers
from app.core.logging import RequestIdMiddleware, configure_logging
from app.core.rate_limit import limiter, rate_limit_handler

# El ida y vuelta con Google dura segundos: una vida corta reduce la ventana en
# la que un `state` viejo podría reutilizarse.
OAUTH_SESSION_MAX_AGE = 10 * 60


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

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
    register_error_handlers(app)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.jwt_secret,
        session_cookie="mc_oauth",
        max_age=OAUTH_SESSION_MAX_AGE,
        # `lax` fijo, no `COOKIE_SAMESITE`: esta cookie tiene que sobrevivir la
        # vuelta desde Google, que es una navegación de primer nivel hacia la
        # propia API (mismo sitio), y `lax` ya la permite.
        same_site="lax",
        https_only=settings.app_env == "production",
    )
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
    app.include_router(users.router, prefix=settings.api_prefix)
    app.include_router(settings_routes.router, prefix=settings.api_prefix)
    app.include_router(shift.router, prefix=settings.api_prefix)

    return app


app = create_app()
