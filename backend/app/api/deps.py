"""Dependencias de FastAPI para autenticación/autorización (Tema 1.5).

``get_current_user`` valida el **access token** (Bearer, nunca la cookie de
refresh) y carga el ``User`` correspondiente. ``require_role`` se apoya en
ella para además exigir que el usuario tenga uno de los roles indicados.
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.enums import Role, UserStatus
from app.core.errors import ForbiddenError, NotAuthenticatedError
from app.core.security import TokenError, decode_token
from app.db.session import get_session
from app.models.user import User
from app.repositories.user_repository import UserRepository

_SESSION_INVALID_MESSAGE = "Necesitás iniciar sesión."

# ``auto_error=False``: preferimos lanzar nuestro propio NotAuthenticatedError
# (formato único de error) en vez del 403 genérico que tira HTTPBearer cuando
# falta el header Authorization.
_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_session),
) -> User:
    """Extrae el Bearer del header ``Authorization``, decodifica el access
    token y carga el usuario. Lanza :class:`NotAuthenticatedError` (401) si
    falta el header, el token es inválido/venció, o el usuario ya no existe
    o no está ``ACTIVE``."""
    if credentials is None:
        raise NotAuthenticatedError(_SESSION_INVALID_MESSAGE)

    try:
        payload = decode_token(credentials.credentials, expected_type="access")
    except TokenError as exc:
        raise NotAuthenticatedError(_SESSION_INVALID_MESSAGE) from exc

    user = UserRepository(db).get_by_id(int(payload["sub"]))
    if user is None or user.status != UserStatus.ACTIVE:
        raise NotAuthenticatedError(_SESSION_INVALID_MESSAGE)
    return user


def require_role(*roles: Role) -> Callable[[User], User]:
    """Fábrica de dependencia: exige sesión válida (``get_current_user``) y
    además que ``user.role`` esté entre ``roles``. Sin coincidencia, 403.

    Uso: ``Depends(require_role(Role.ADMIN))`` o con varios roles permitidos,
    ``Depends(require_role(Role.ADMIN, Role.DELIVERY))``.
    """

    def _dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise ForbiddenError()
        return user

    return _dependency


__all__ = ["get_current_user", "require_role"]
