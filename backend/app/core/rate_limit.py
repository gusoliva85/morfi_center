from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# Límite de los endpoints sensibles a fuerza bruta (§22 del Documento Técnico).
AUTH_RATE_LIMIT = "10/minute"

# La IP sale de `request.client.host`. En producción la API está detrás de Nginx,
# que manda la IP real en `X-Forwarded-For`, y Uvicorn la usa porque confía en
# los proxy headers que vienen de 127.0.0.1 (su default). Sin eso, todas las
# requests parecerían venir de Nginx y un solo atacante agotaría el límite de
# todos los usuarios a la vez.
limiter = Limiter(key_func=get_remote_address)

TOO_MANY_REQUESTS = "Demasiados intentos. Esperá un momento y volvé a probar."


async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Mismo formato de error que el resto de la API (§20.1); slowapi trae su
    propio formato por defecto, distinto al del proyecto."""
    return JSONResponse(
        status_code=429,
        content={
            "error": {
                "code": "TOO_MANY_REQUESTS",
                "message": TOO_MANY_REQUESTS,
                "details": {"limit": exc.detail},
            }
        },
        headers={"Retry-After": "60"},
    )
