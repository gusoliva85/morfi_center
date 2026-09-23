from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.enums import UserStatus
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
