"""Configuración de logging y contexto de request.

- ``configure_logging()``: formato legible en desarrollo, JSON por línea en producción.
- ``RequestContextMiddleware``: ASGI middleware que asigna un ``request_id`` por
  request (respeta el header entrante ``X-Request-Id`` o genera uno), lo propaga a
  todos los logs de esa request y lo devuelve en el header ``X-Request-Id``.
- ``bind_user_id(...)``: lo llama la dependencia de autenticación (Fase 1) para que
  el ``user_id`` aparezca en los logs.

Referencia: ``documentacion/02_Documento_Tecnico.md`` §20.2.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from contextvars import ContextVar
from datetime import UTC, datetime
from uuid import uuid4

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import settings

# ── Contexto por request ────────────────────────────────
_request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)
_user_id_ctx: ContextVar[int | None] = ContextVar("user_id", default=None)

_ACCESS_LOGGER = "morfi.access"


def get_request_id() -> str | None:
    return _request_id_ctx.get()


def bind_user_id(user_id: int | None) -> None:
    """Asocia un user_id al contexto de logging de la request actual.

    Llamar desde una dependencia ``async`` (así lo hace ``get_current_user`` en
    Fase 1) para que el valor sea visible tanto en los logs de la request como en
    la línea de acceso final. Si se llama desde código sync ejecutado en el
    threadpool, el cambio queda aislado en ese hilo.
    """
    _user_id_ctx.set(user_id)


# ── Filtro e formatters ─────────────────────────────────
class _ContextFilter(logging.Filter):
    """Inyecta request_id / user_id (del contexto) en cada LogRecord."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = _request_id_ctx.get() or "-"
        if not hasattr(record, "user_id"):
            record.user_id = _user_id_ctx.get()
        return True


class _JsonFormatter(logging.Formatter):
    _EXTRA_KEYS = ("method", "path", "status_code", "duration_ms")

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", "-"),
            "msg": record.getMessage(),
        }
        user_id = getattr(record, "user_id", None)
        if user_id is not None:
            payload["user_id"] = user_id
        for key in self._EXTRA_KEYS:
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


_DEV_FORMAT = "%(asctime)s %(levelname)-7s %(name)-16s [%(request_id)s] %(message)s"


def configure_logging() -> None:
    """Configura el logger raíz. Idempotente (reemplaza los handlers)."""
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(_ContextFilter())
    if settings.is_production:
        handler.setFormatter(_JsonFormatter())
        root.setLevel(logging.INFO)
    else:
        handler.setFormatter(logging.Formatter(_DEV_FORMAT, datefmt="%H:%M:%S"))
        root.setLevel(logging.DEBUG)
    root.addHandler(handler)

    # uvicorn ya loguea acceso; usamos el nuestro (estructurado) como fuente única.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    # librerías ruidosas en DEBUG (dev): dejarlas en WARNING/INFO.
    for noisy in ("httpx", "httpcore", "multipart", "asyncio", "apscheduler"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


# ── Middleware ──────────────────────────────────────────
_MUTATION_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _incoming_request_id(scope: Scope) -> str:
    for name, value in scope.get("headers", []):
        if name == b"x-request-id":
            candidate = value.decode("latin-1").strip()[:64]
            if candidate:
                return candidate
    return uuid4().hex


class RequestContextMiddleware:
    """ASGI middleware: request_id en contexto + header + log de acceso."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = _incoming_request_id(scope)
        token = _request_id_ctx.set(request_id)
        user_token = _user_id_ctx.set(None)
        started = time.perf_counter()
        status_code = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                MutableHeaders(scope=message)["X-Request-Id"] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000, 1)
            method = scope.get("method", "?")
            path = scope.get("path", "")
            if status_code >= 500:
                level = logging.ERROR
            elif method in _MUTATION_METHODS:
                level = logging.INFO
            else:
                level = logging.DEBUG
            logging.getLogger(_ACCESS_LOGGER).log(
                level,
                "%s %s -> %s (%s ms)",
                method,
                path,
                status_code,
                duration_ms,
                extra={
                    "request_id": request_id,
                    "user_id": _user_id_ctx.get(),
                    "method": method,
                    "path": path,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                },
            )
            _user_id_ctx.reset(user_token)
            _request_id_ctx.reset(token)


__all__ = [
    "configure_logging",
    "RequestContextMiddleware",
    "get_request_id",
    "bind_user_id",
]
