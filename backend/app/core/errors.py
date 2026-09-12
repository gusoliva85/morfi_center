"""Errores de dominio y handlers globales de la API.

Toda regla de negocio lanza una subclase de :class:`DomainError` (nunca una
``HTTPException``). Los handlers registrados con :func:`register_error_handlers`
las traducen al formato único de error de la API::

    {"error": {"code": "...", "message": "...", "details": {...}}}

Referencia: ``documentacion/02_Documento_Tecnico.md`` §20.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("morfi.errors")


# ══════════════════════════════════════════════════════════
#  Excepciones de dominio
# ══════════════════════════════════════════════════════════


class DomainError(Exception):
    """Error de negocio. Cada subclase fija ``status_code`` y ``code``."""

    status_code: int = 409
    code: str = "DOMAIN_ERROR"
    default_message: str = "No se pudo completar la operación."

    def __init__(
        self,
        message: str | None = None,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message or self.default_message
        self.details: dict[str, Any] = details or {}
        super().__init__(self.message)

    def to_payload(self) -> dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            }
        }


class NotFoundError(DomainError):
    status_code = 404
    code = "NOT_FOUND"
    default_message = "El recurso solicitado no existe."


class NotAuthenticatedError(DomainError):
    status_code = 401
    code = "NOT_AUTHENTICATED"
    default_message = "Necesitás iniciar sesión."


class ForbiddenError(DomainError):
    status_code = 403
    code = "FORBIDDEN"
    default_message = "No tenés permiso para realizar esta acción."


class ConflictError(DomainError):
    status_code = 409
    code = "CONFLICT"
    default_message = "La operación entra en conflicto con el estado actual."


class InvalidInputError(DomainError):
    status_code = 400
    code = "INVALID_INPUT"
    default_message = "Los datos enviados no son válidos."


class AddressNotGeocodableError(DomainError):
    status_code = 400
    code = "ADDRESS_NOT_GEOCODABLE"
    default_message = "No pudimos ubicar esa dirección en el mapa."


class OutOfStockError(DomainError):
    status_code = 409
    code = "OUT_OF_STOCK"
    default_message = "No hay stock suficiente para completar el pedido."


class ShiftClosedError(DomainError):
    status_code = 409
    code = "SHIFT_CLOSED"
    default_message = "Los pedidos para este turno ya están cerrados."


class CancelWindowClosedError(DomainError):
    status_code = 409
    code = "CANCEL_WINDOW_CLOSED"
    default_message = "La cancelación ya no está disponible para este turno."


class OutOfCoverageError(DomainError):
    status_code = 409
    code = "OUT_OF_COVERAGE"
    default_message = "La dirección está fuera de la zona de entrega."


class InvalidTransitionError(DomainError):
    status_code = 409
    code = "INVALID_TRANSITION"
    default_message = "El pedido no puede pasar a ese estado."


class FileTooLargeError(DomainError):
    status_code = 413
    code = "FILE_TOO_LARGE"
    default_message = "El archivo supera el tamaño máximo permitido."


# ══════════════════════════════════════════════════════════
#  Traducción a respuesta HTTP
# ══════════════════════════════════════════════════════════

# status HTTP -> code para HTTPException "sueltas" (routing 404, 405, etc.)
_HTTP_STATUS_CODE: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "NOT_AUTHENTICATED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    413: "FILE_TOO_LARGE",
    422: "VALIDATION_ERROR",
    429: "TOO_MANY_REQUESTS",
}


def _payload(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details or {}}}


async def _domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=exc.to_payload())


async def _validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=_payload(
            "VALIDATION_ERROR",
            "Hay campos con datos inválidos.",
            {"fields": jsonable_encoder(exc.errors())},
        ),
    )


async def _http_exception_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = _HTTP_STATUS_CODE.get(exc.status_code, f"HTTP_{exc.status_code}")
    message = exc.detail if isinstance(exc.detail, str) else "Ocurrió un error en la solicitud."
    return JSONResponse(status_code=exc.status_code, content=_payload(code, message))


async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Error no controlado en %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content=_payload(
            "INTERNAL_ERROR",
            "Ocurrió un error interno. Ya quedó registrado.",
        ),
    )


def register_error_handlers(app: FastAPI) -> None:
    """Registra en la app FastAPI los handlers que unifican el formato de error."""
    app.add_exception_handler(DomainError, _domain_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_exception_handler(Exception, _unhandled_exception_handler)


__all__ = [
    "DomainError",
    "NotFoundError",
    "NotAuthenticatedError",
    "ForbiddenError",
    "ConflictError",
    "InvalidInputError",
    "AddressNotGeocodableError",
    "OutOfStockError",
    "ShiftClosedError",
    "CancelWindowClosedError",
    "OutOfCoverageError",
    "InvalidTransitionError",
    "FileTooLargeError",
    "register_error_handlers",
]
