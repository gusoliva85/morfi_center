"""Rate limiting (slowapi) para endpoints sensibles de autenticación.

Limita por IP de origen. `DEFAULT_AUTH_LIMIT` es el límite por defecto para
login/registro/recuperación de contraseña (`documentacion/02_Documento_Tecnico.md`
§18): 10 intentos por minuto. Cada endpoint puede pedir el suyo con
``@limiter.limit("N/minute")``.

``limiter`` es un singleton de módulo (igual que en producción): en los tests
hay que resetear su storage entre tests para que no arrastren cupo de un test
al siguiente — ver el fixture ``_reset_rate_limiter`` en ``tests/conftest.py``.
"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

DEFAULT_AUTH_LIMIT = "10/minute"

limiter = Limiter(key_func=get_remote_address)


async def rate_limit_exceeded_handler(_: Request, __: RateLimitExceeded) -> JSONResponse:
    """Traduce el 429 de slowapi al formato único de error de la API (§20)."""
    return JSONResponse(
        status_code=429,
        content={
            "error": {
                "code": "TOO_MANY_REQUESTS",
                "message": "Hiciste demasiados intentos. Esperá un momento y volvé a intentar.",
                "details": {},
            }
        },
    )


__all__ = ["limiter", "rate_limit_exceeded_handler", "DEFAULT_AUTH_LIMIT"]
