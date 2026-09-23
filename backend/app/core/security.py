import uuid
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any, Protocol

import bcrypt
import jwt

from app.core.config import settings
from app.core.errors import TokenExpiredError, TokenInvalidError

_ROUNDS = 12
_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=_ROUNDS))
    return hashed.decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


class _UserLike(Protocol):
    """Lo mínimo que necesitan los tokens — no depende del modelo User (Fase 1, T-1.2.1)."""

    id: int
    role: str


def create_access_token(user: _UserLike) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user.id),
        "role": user.role,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM)


def create_refresh_token(user: _UserLike) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user.id),
        "type": "refresh",
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(days=settings.refresh_token_days),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM)


def password_fingerprint(password_hash: str | None) -> str:
    """Huella corta del estado actual de la contraseña.

    Va dentro del token de reseteo para que, apenas la contraseña cambia, todos
    los links de recuperación emitidos antes queden inservibles: si no, alguien
    con un link viejo (de un mail reenviado, por ejemplo) podría volver a
    cambiarla durante los 30 minutos siguientes.
    """
    return sha256((password_hash or "sin-contrasena").encode("utf-8")).hexdigest()[:16]


def create_password_reset_token(user: _UserLike, password_hash: str | None) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user.id),
        "type": "password_reset",
        "jti": str(uuid.uuid4()),
        "pwd": password_fingerprint(password_hash),
        "iat": now,
        "exp": now + timedelta(minutes=settings.password_reset_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpiredError("El token expiró.") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenInvalidError("Token inválido.") from exc
