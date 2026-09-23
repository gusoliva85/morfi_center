import logging
from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Cookie, Request, Response, status
from fastapi.responses import RedirectResponse

from app.api.deps import CurrentUser, SessionDep
from app.core.config import settings
from app.core.errors import ForbiddenError, NotAuthenticatedError, ServiceUnavailableError
from app.core.oauth import google_is_configured, oauth
from app.core.rate_limit import AUTH_RATE_LIMIT, limiter
from app.core.security import create_access_token, create_refresh_token
from app.models import User
from app.schemas.auth import (
    LoginIn,
    MessageOut,
    PasswordForgotIn,
    PasswordResetIn,
    RegisterIn,
    TokenOut,
)
from app.schemas.user import MeOut, UserOut
from app.services.auth_service import SESSION_EXPIRED, AuthService

REFRESH_COOKIE_NAME = "mc_refresh"

logger = logging.getLogger(__name__)

PASSWORD_RESET_SENT = (
    "Si ese email tiene una cuenta, te enviamos un link para cambiar la contraseña."
)
PASSWORD_CHANGED = "Tu contraseña se cambió. Ya podés iniciar sesión."

GOOGLE_NOT_CONFIGURED = (
    "El ingreso con Google no está disponible por ahora. Entrá con tu email y contraseña."
)

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


@router.post("/password/forgot", response_model=MessageOut)
@limiter.limit(AUTH_RATE_LIMIT)
def password_forgot(request: Request, data: PasswordForgotIn, session: SessionDep) -> MessageOut:
    """Pide un link de recuperación.

    Responde **siempre** lo mismo, exista o no el email: si distinguiera, serviría
    para averiguar qué emails están registrados.
    """
    result = AuthService(session).request_password_reset(data.email)

    if result is not None:
        user, token = result
        # Todavía no hay servicio de mail en el stack: el link se loguea en el
        # servidor. Ver la nota de T-1.9.1 en el roadmap.
        logger.warning(
            "Link de recuperación para %s: %s/pages/auth/recuperar.html?token=%s",
            user.email,
            settings.frontend_origin.rstrip("/"),
            token,
        )

    return MessageOut(message=PASSWORD_RESET_SENT)


@router.post("/password/reset", response_model=MessageOut)
@limiter.limit(AUTH_RATE_LIMIT)
def password_reset(request: Request, data: PasswordResetIn, session: SessionDep) -> MessageOut:
    """Cambia la contraseña con el token del link. El link sirve una sola vez."""
    AuthService(session).reset_password(data.token, data.password)
    return MessageOut(message=PASSWORD_CHANGED)


@router.get("/google/login")
async def google_login(request: Request) -> RedirectResponse:
    """Manda al usuario a la pantalla de Google. Authlib agrega el `state` y el
    PKCE, y los guarda en la sesión firmada para verificarlos en la vuelta."""
    if not google_is_configured():
        raise ServiceUnavailableError(GOOGLE_NOT_CONFIGURED)

    return await oauth.google.authorize_redirect(request, settings.google_redirect_uri)


def _front_redirect(path: str = "/", **params: str) -> RedirectResponse:
    query = f"?{urlencode(params)}" if params else ""
    return RedirectResponse(f"{settings.frontend_origin.rstrip('/')}{path}{query}")


@router.get("/google/callback")
async def google_callback(request: Request, session: SessionDep) -> RedirectResponse:
    """Vuelta desde Google. Termina siempre en el front, no en un JSON: acá está
    el navegador de una persona, no un cliente de API.

    No manda el access token en la URL (quedaría en el historial, en los logs y
    en el `Referer`): deja la cookie de refresh y el front pide el access con
    `/auth/refresh` al cargar, que es lo que ya hace al iniciar.
    """
    if not google_is_configured():
        raise ServiceUnavailableError(GOOGLE_NOT_CONFIGURED)

    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception:
        # `state` que no coincide, código vencido, o el usuario canceló.
        logger.warning("Fallo el intercambio de código con Google", exc_info=True)
        return _front_redirect(auth_error="google")

    claims = token.get("userinfo") or {}
    if not claims.get("email") or not claims.get("sub"):
        logger.warning("Google no devolvió email o sub en el id_token")
        return _front_redirect(auth_error="google")

    if not claims.get("email_verified"):
        # Sin email confirmado, vincular permitiría reclamar la cuenta de otro.
        logger.warning("Google devolvió un email sin verificar")
        return _front_redirect(auth_error="google_email_unverified")

    try:
        user = AuthService(session).login_with_google(
            sub=str(claims["sub"]),
            email=claims["email"],
            first_name=claims.get("given_name", ""),
            last_name=claims.get("family_name", ""),
        )
    except ForbiddenError:
        return _front_redirect(auth_error="account_not_active")

    response = _front_redirect()
    set_refresh_cookie(response, user)
    return response


@router.get("/me", response_model=MeOut)
def me(user: CurrentUser) -> MeOut:
    """Quién es el usuario de la sesión actual. El front lo llama al cargar cada
    página para saludarlo y decidir qué mostrar."""
    return MeOut.from_user(user)


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
