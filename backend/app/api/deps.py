from collections.abc import Callable
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.enums import Role, UserStatus
from app.core.errors import ForbiddenError, NotAuthenticatedError, TokenInvalidError
from app.core.security import decode_token
from app.db.session import get_session
from app.models import User
from app.repositories.user_repository import UserRepository
from app.services.auth_service import ACCOUNT_NOT_ACTIVE

NOT_AUTHENTICATED = "Necesitás iniciar sesión."

SessionDep = Annotated[Session, Depends(get_session)]

# auto_error=False para manejar el "falta el header" con el formato de error del
# proyecto (§20.1): el default de HTTPBearer larga su propio 403 de FastAPI.
_bearer = HTTPBearer(auto_error=False)
BearerDep = Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]


def get_current_user(session: SessionDep, credentials: BearerDep) -> User:
    """Usuario dueño del access token del header `Authorization: Bearer`.

    Solo acepta tokens de tipo `access`: el refresh vive en una cookie y sirve
    únicamente para renovar la sesión, así que aceptarlo acá saltearía la
    rotación de un solo uso de `T-1.4.3`.
    """
    if credentials is None or not credentials.credentials:
        raise NotAuthenticatedError(NOT_AUTHENTICATED)

    payload = decode_token(credentials.credentials)  # 401 si venció o es inválido
    if payload.get("type") != "access":
        raise TokenInvalidError(NOT_AUTHENTICATED)

    user = UserRepository(session).get_by_id(int(payload["sub"]))
    if user is None:
        raise TokenInvalidError(NOT_AUTHENTICATED)
    if user.status != UserStatus.ACTIVE:
        # Suspender a alguien tiene que echarlo ya, sin esperar a que venza su
        # access token (hasta 15 min de acceso con la cuenta deshabilitada).
        raise ForbiddenError(ACCOUNT_NOT_ACTIVE)

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]

NOT_ALLOWED = "No tenés permiso para hacer esto."


def require_role(*roles: Role) -> Callable[[User], User]:
    """Dependencia que exige uno de esos roles y devuelve el usuario.

    Sin argumentos exige solo tener sesión (cualquier rol logueado): es lo que
    usan las pantallas de cliente, que no se atan a `CUSTOMER` porque un admin
    también puede querer pedir comida (ver `T-1.11.4` y RN-33).

    Devuelve el usuario, no `None`, para que el endpoint no tenga que pedir
    `get_current_user` otra vez por separado.
    """

    def dependency(user: CurrentUser) -> User:
        if roles and user.role not in roles:
            raise ForbiddenError(NOT_ALLOWED)
        return user

    return dependency


AdminUser = Annotated[User, Depends(require_role(Role.ADMIN))]
DeliveryUser = Annotated[User, Depends(require_role(Role.DELIVERY))]
LoggedInUser = Annotated[User, Depends(require_role())]
