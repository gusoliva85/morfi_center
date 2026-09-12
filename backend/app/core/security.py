"""Hashing de contraseñas y tokens JWT (access + refresh).

Capa de **lógica pura**: no conoce FastAPI ni el modelo ``User`` (todavía no
existe — llega en el Tema 1.2). Las funciones de token reciben el id y el rol
directamente; la dependencia de FastAPI (Tema 1.5) las conecta con la request.

- Contraseñas: bcrypt (passlib) con costo 12, ver §18 de ``02_Documento_Tecnico.md``.
- Tokens: JWT firmado con ``settings.jwt_secret`` / ``settings.jwt_algorithm``.
  Access: corta duración, claims ``sub``, ``role``, ``type=access``.
  Refresh: larga duración, claims ``sub``, ``jti``, ``type=refresh``.
  Los errores de token son propios de este módulo (``TokenExpiredError`` /
  ``TokenInvalidError``), no ``DomainError``: la traducción a 401 la hace la
  dependencia de auth (Tema 1.5), no esta capa.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import uuid4

import jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.timezone import now_utc

# ══════════════════════════════════════════════════════════
#  Contraseñas
# ══════════════════════════════════════════════════════════

BCRYPT_ROUNDS = 12

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=BCRYPT_ROUNDS)


def hash_password(password: str) -> str:
    """Genera el hash bcrypt de una contraseña en texto plano.

    :raises ValueError: si la contraseña está vacía (validar el contenido con
        ``user_service.validate_password`` antes de llegar acá).
    """
    if not password:
        raise ValueError("La contraseña no puede estar vacía.")
    return _pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Compara una contraseña en texto plano contra un hash.

    Nunca lanza: una entrada vacía, un hash malformado o un esquema
    desconocido se tratan como "no coincide" (``False``), no como error.
    """
    if not password or not password_hash:
        return False
    try:
        return _pwd_context.verify(password, password_hash)
    except (ValueError, TypeError):
        return False


def needs_rehash(password_hash: str) -> bool:
    """True si el hash fue generado con parámetros distintos a los actuales
    (p. ej. un costo bcrypt más bajo) y conviene regenerarlo."""
    try:
        return _pwd_context.needs_update(password_hash)
    except (ValueError, TypeError):
        return True


# ══════════════════════════════════════════════════════════
#  JWT (access + refresh)
# ══════════════════════════════════════════════════════════


class TokenError(Exception):
    """Base de los errores de token. No es un DomainError a propósito: la
    traducción a HTTP 401 la hace la dependencia de autenticación."""


class TokenExpiredError(TokenError):
    """El token es válido pero ya venció."""


class TokenInvalidError(TokenError):
    """El token está mal formado, tiene firma inválida o el tipo no coincide."""


def _encode(payload: dict[str, Any]) -> str:
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(
    user_id: int | str, role: str, *, expires_minutes: int | None = None, now=None
) -> str:
    """Access token de corta duración. Claims: ``sub``, ``role``, ``type=access``."""
    issued_at = now or now_utc()
    minutes = settings.access_token_minutes if expires_minutes is None else expires_minutes
    payload = {
        "sub": str(user_id),
        "role": str(role),
        "type": "access",
        "iat": int(issued_at.timestamp()),
        "exp": int((issued_at + timedelta(minutes=minutes)).timestamp()),
    }
    return _encode(payload)


def create_refresh_token(
    user_id: int | str,
    *,
    expires_days: int | None = None,
    jti: str | None = None,
    now=None,
) -> tuple[str, str]:
    """Refresh token de larga duración. Claims: ``sub``, ``jti``, ``type=refresh``.

    Devuelve ``(token, jti)`` — el ``jti`` se guarda/rota en el Tema 1.4 para
    poder revocar sesiones.
    """
    issued_at = now or now_utc()
    days = settings.refresh_token_days if expires_days is None else expires_days
    token_id = jti or uuid4().hex
    payload = {
        "sub": str(user_id),
        "jti": token_id,
        "type": "refresh",
        "iat": int(issued_at.timestamp()),
        "exp": int((issued_at + timedelta(days=days)).timestamp()),
    }
    return _encode(payload), token_id


def create_password_reset_token(
    user_id: int | str,
    *,
    expires_minutes: int | None = None,
    jti: str | None = None,
    now=None,
) -> tuple[str, str]:
    """Token de reseteo de contraseña. Claims: ``sub``, ``jti``, ``type=password_reset``.

    Mismo patrón que el refresh (``jti`` para poder revocarlo — uso único,
    ver ``AuthService.reset_password`` en el Tema 1.9). Vigencia por defecto:
    ``settings.password_reset_token_minutes`` (30 min).

    Devuelve ``(token, jti)``.
    """
    issued_at = now or now_utc()
    minutes = settings.password_reset_token_minutes if expires_minutes is None else expires_minutes
    token_id = jti or uuid4().hex
    payload = {
        "sub": str(user_id),
        "jti": token_id,
        "type": "password_reset",
        "iat": int(issued_at.timestamp()),
        "exp": int((issued_at + timedelta(minutes=minutes)).timestamp()),
    }
    return _encode(payload), token_id


def decode_token(token: str, *, expected_type: str | None = None) -> dict[str, Any]:
    """Decodifica y valida un JWT propio.

    :raises TokenExpiredError: si venció.
    :raises TokenInvalidError: si la firma/formato no son válidos, o si
        ``expected_type`` no coincide con el claim ``type`` del token.
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpiredError("El token expiró.") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenInvalidError("El token no es válido.") from exc

    if expected_type and payload.get("type") != expected_type:
        raise TokenInvalidError(f"Se esperaba un token de tipo '{expected_type}'.")
    return payload


__all__ = [
    "hash_password",
    "verify_password",
    "needs_rehash",
    "BCRYPT_ROUNDS",
    "TokenError",
    "TokenExpiredError",
    "TokenInvalidError",
    "create_access_token",
    "create_refresh_token",
    "create_password_reset_token",
    "decode_token",
]
