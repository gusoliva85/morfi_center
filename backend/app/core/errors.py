from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class DomainError(Exception):
    """Excepción base de las reglas de negocio. Nunca se lanza HTTPException fuera de api/."""

    status_code: int = 500
    code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(DomainError):
    status_code = 404
    code = "NOT_FOUND"


class ForbiddenError(DomainError):
    status_code = 403
    code = "FORBIDDEN"


class ConflictError(DomainError):
    status_code = 409
    code = "CONFLICT"


class DomainValidationError(DomainError):
    """Un valor que no cumple las reglas del negocio (no solo el formato del
    request). Mismo código y forma de `details` que el 422 de Pydantic (§20.1),
    así el front maneja un único formato de error de validación."""

    status_code = 422
    code = "VALIDATION_ERROR"


class SettingCorruptError(DomainError):
    """Una configuración guardada en la base ya no tiene la forma esperada
    (alguien la tocó a mano). Se falla en vez de asumir un valor: un horario o
    unos datos de transferencia equivocados salen caros."""

    status_code = 500
    code = "SETTING_CORRUPT"


class OutOfStockError(DomainError):
    status_code = 409
    code = "OUT_OF_STOCK"


class ShiftClosedError(DomainError):
    status_code = 409
    code = "SHIFT_CLOSED"


class CancelWindowClosedError(DomainError):
    status_code = 409
    code = "CANCEL_WINDOW_CLOSED"


class OutOfCoverageError(DomainError):
    status_code = 409
    code = "OUT_OF_COVERAGE"


class InvalidTransitionError(DomainError):
    status_code = 409
    code = "INVALID_TRANSITION"


class ServiceUnavailableError(DomainError):
    """Una integración externa no está disponible o no está configurada."""

    status_code = 503
    code = "SERVICE_UNAVAILABLE"


class NotAuthenticatedError(DomainError):
    """Credenciales inválidas o sesión ausente."""

    status_code = 401
    code = "NOT_AUTHENTICATED"


class TokenExpiredError(DomainError):
    """JWT válido en su momento pero ya vencido (access o refresh)."""

    status_code = 401
    code = "NOT_AUTHENTICATED"


class TokenInvalidError(DomainError):
    """JWT malformado, con firma inválida, o de un tipo inesperado."""

    status_code = 401
    code = "NOT_AUTHENTICATED"


async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Traduce los 422 de Pydantic al formato de error del proyecto (§20.1).
    Sin esto, FastAPI responde su `{"detail": [...]}` por defecto y el front
    tendría que entender dos formatos de error distintos."""
    fields = [
        {
            "field": ".".join(str(part) for part in error["loc"] if part != "body"),
            "message": error["msg"].removeprefix("Value error, "),
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Los datos enviados no son válidos.",
                "details": {"fields": fields},
            }
        },
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, domain_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
