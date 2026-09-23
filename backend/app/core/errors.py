from typing import Any

from fastapi import FastAPI, Request
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


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, domain_error_handler)
