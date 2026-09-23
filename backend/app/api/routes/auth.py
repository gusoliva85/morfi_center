from typing import Annotated

from fastapi import APIRouter, Cookie, Request, Response, status

from app.api.deps import SessionDep
from app.core.config import settings
from app.core.errors import NotAuthenticatedError
from app.core.rate_limit import AUTH_RATE_LIMIT, limiter
from app.core.security import create_access_token, create_refresh_token
from app.models import User
from app.schemas.auth import LoginIn, RegisterIn, TokenOut
from app.schemas.user import UserOut
from app.services.auth_service import SESSION_EXPIRED, AuthService

REFRESH_COOKIE_NAME = "mc_refresh"

router = APIRouter(prefix="/auth", tags=["auth"])


def refresh_cookie_path() -> str:
    """Path acotado: la cookie solo se manda a los endpoints de auth (§16.1)."""
    return f"{settings.api_prefix}/auth"


def set_refresh_cookie(response: Response, user: User) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=create_refresh_token(user),
        httponly=True,
        # En producción el front está en Vercel y la API en el VPS: es cross-site
        # real, así que la cookie necesita SameSite=None, que a su vez exige
        # Secure (§17). En desarrollo es http://localhost, donde Secure la
        # bloquearía.
        secure=settings.app_env == "production",
        samesite=settings.cookie_samesite,
        path=refresh_cookie_path(),
        max_age=settings.refresh_token_days * 24 * 60 * 60,
    )


def session_response(user: User) -> TokenOut:
    return TokenOut(
        access_token=create_access_token(user),
        expires_in=settings.access_token_minutes * 60,
        user=UserOut.model_validate(user),
    )


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
@limiter.limit(AUTH_RATE_LIMIT)
def register(
    request: Request,  # lo exige slowapi para sacar la IP; no se usa en el cuerpo
    data: RegisterIn,
    response: Response,
    session: SessionDep,
) -> TokenOut:
    """Alta de cliente con login automático: devuelve el access token y deja la
    cookie de refresh, igual que el login."""
    user = AuthService(session).register(
        first_name=data.first_name,
        last_name=data.last_name,
        email=data.email,
        password=data.password,
        phone=data.phone,
    )
    set_refresh_cookie(response, user)
    return session_response(user)


@router.post("/login", response_model=TokenOut)
@limiter.limit(AUTH_RATE_LIMIT)
def login(
    request: Request,
    data: LoginIn,
    response: Response,
    session: SessionDep,
) -> TokenOut:
    user = AuthService(session).authenticate(email=data.email, password=data.password)
    set_refresh_cookie(response, user)
    return session_response(user)


@router.post("/refresh", response_model=TokenOut)
def refresh(
    response: Response,
    session: SessionDep,
    mc_refresh: Annotated[str | None, Cookie()] = None,
) -> TokenOut:
    """Renueva la sesión a partir de la cookie. El refresh viejo queda quemado:
    cada llamada entrega uno nuevo (rotación de un solo uso)."""
    if not mc_refresh:
        raise NotAuthenticatedError(SESSION_EXPIRED)

    user = AuthService(session).rotate_refresh(mc_refresh)
    set_refresh_cookie(response, user)
    return session_response(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    session: SessionDep,
    mc_refresh: Annotated[str | None, Cookie()] = None,
) -> None:
    """Cierra la sesión: quema el refresh y borra la cookie. Siempre responde
    204, incluso sin sesión — cerrar sesión nunca debería poder fallar."""
    AuthService(session).logout(mc_refresh)
    # Los mismos atributos que al crearla: si el path o el samesite no coinciden,
    # el navegador no la reconoce como la misma cookie y no la borra.
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=refresh_cookie_path(),
        httponly=True,
        secure=settings.app_env == "production",
        samesite=settings.cookie_samesite,
    )
