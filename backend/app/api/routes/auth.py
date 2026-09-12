"""Endpoints de autenticación.

Convenciones de esta fase (ver ``documentacion/02_Documento_Tecnico.md`` §13):
- El **access token** viaja en el cuerpo de la respuesta (`AuthOut.access_token`).
- El **refresh token** viaja en una cookie httpOnly (`mc_refresh`), acotada a
  ``/api/v1/auth`` — nunca en el cuerpo ni accesible por JavaScript.
"""

# NOTA: sin `from __future__ import annotations` a propósito en este archivo.
# El decorador @limiter.limit (slowapi) envuelve la función de la ruta de una
# forma que, combinada con anotaciones diferidas (PEP 563), le impide a
# FastAPI/Pydantic resolver los forward refs de los parámetros (ej. `RegisterIn`)
# al generar el schema — rompe el OpenAPI y, con él, la validación de todas las
# rutas de este router. Es una incompatibilidad conocida de slowapi; el resto
# del proyecto sigue usando anotaciones diferidas normalmente.

import logging

import jwt
from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.errors import ForbiddenError
from app.core.rate_limit import DEFAULT_AUTH_LIMIT, limiter
from app.core.security import create_access_token, create_refresh_token
from app.db.session import get_session
from app.models.user import User
from app.schemas.auth import (
    AuthOut,
    ForgotPasswordIn,
    ForgotPasswordOut,
    LoginIn,
    LogoutOut,
    ResetPasswordIn,
    ResetPasswordOut,
)
from app.schemas.user import MeOut, RegisterIn, UserOut
from app.services.auth_service import AuthService
from app.services.external.google_oauth import (
    OAUTH_STATE_COOKIE_NAME,
    OAUTH_STATE_COOKIE_PATH,
    OAUTH_STATE_TTL_MINUTES,
    build_authorization_redirect,
    exchange_code_for_tokens,
    verify_google_id_token,
)

logger = logging.getLogger("morfi.auth")

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE_NAME = "mc_refresh"
REFRESH_COOKIE_PATH = f"{settings.api_prefix}/auth"

# Página del front donde cae el usuario después del flujo de Google (éxito o
# error) — hoy es la misma que tiene el botón "Continuar con Google" (T-1.11.1).
GOOGLE_CALLBACK_FRONT_PATH = "/pages/auth/login.html"


def set_refresh_cookie(response: Response, token: str) -> None:
    """Setea la cookie de refresh con los flags de seguridad correspondientes."""
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        max_age=settings.refresh_token_days * 86400,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        path=REFRESH_COOKIE_PATH,
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)


def issue_tokens(response: Response, user: User) -> AuthOut:
    """Emite un par access+refresh para `user`: setea la cookie de refresh y
    arma la respuesta con el access token + los datos públicos del usuario."""
    access_token = create_access_token(user.id, user.role)
    refresh_token, _jti = create_refresh_token(user.id)
    set_refresh_cookie(response, refresh_token)
    return AuthOut(
        access_token=access_token,
        expires_in=settings.access_token_minutes * 60,
        user=UserOut.model_validate(user),
    )


@router.post("/register", response_model=AuthOut, status_code=status.HTTP_201_CREATED)
@limiter.limit(DEFAULT_AUTH_LIMIT)
def register(
    request: Request,  # lo exige el decorador @limiter.limit (slowapi)
    payload: RegisterIn,
    response: Response,
    db: Session = Depends(get_session),
) -> AuthOut:
    """Alta de cuenta propia (rol CUSTOMER). Deja al usuario logueado
    (emite tokens) igual que si hiciera login justo después.

    Limitada a ``DEFAULT_AUTH_LIMIT`` por IP para frenar altas automatizadas.
    """
    user = AuthService(db).register(
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        password=payload.password,
        phone=payload.phone,
    )
    return issue_tokens(response, user)


@router.post("/login", response_model=AuthOut)
@limiter.limit(DEFAULT_AUTH_LIMIT)
def login(
    request: Request,  # lo exige el decorador @limiter.limit (slowapi)
    payload: LoginIn,
    response: Response,
    db: Session = Depends(get_session),
) -> AuthOut:
    """Login local. Mismas reglas de `AuthService.authenticate`: credenciales
    inválidas y email inexistente devuelven el mismo 401 genérico; cuenta no
    activa devuelve 403.

    Limitada a ``DEFAULT_AUTH_LIMIT`` por IP para frenar fuerza bruta.
    """
    user = AuthService(db).authenticate(payload.email, payload.password)
    return issue_tokens(response, user)


@router.post("/refresh", response_model=AuthOut)
def refresh(
    request: Request,
    response: Response,
    db: Session = Depends(get_session),
) -> AuthOut:
    """Renueva la sesión a partir de la cookie `mc_refresh`.

    Rota el refresh en cada llamada (jti nuevo); reusar uno ya rotado, uno
    vencido, o llamar sin cookie, devuelve 401.
    """
    token = request.cookies.get(REFRESH_COOKIE_NAME)
    user = AuthService(db).refresh_session(token)
    return issue_tokens(response, user)


@router.post("/logout", response_model=LogoutOut)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_session),
) -> LogoutOut:
    """Cierra la sesión: revoca el refresh actual (si había uno válido) y
    borra la cookie. Siempre responde 200 `{"ok": true}`, incluso sin cookie."""
    token = request.cookies.get(REFRESH_COOKIE_NAME)
    AuthService(db).logout(token)
    clear_refresh_cookie(response)
    return LogoutOut()


@router.post("/password/forgot", response_model=ForgotPasswordOut)
@limiter.limit(DEFAULT_AUTH_LIMIT)
def forgot_password(
    request: Request,  # lo exige el decorador @limiter.limit (slowapi)
    payload: ForgotPasswordIn,
    db: Session = Depends(get_session),
) -> ForgotPasswordOut:
    """Pide un reseteo de contraseña. Siempre responde 200 — no revela si el
    email existe, si la cuenta está activa, ni si es una cuenta local o de
    Google.

    Todavía no hay envío de mail (ver `documentacion/02_Documento_Tecnico.md`
    §14): en dev, el token se loguea en consola en vez de enviarse.

    Limitada a `DEFAULT_AUTH_LIMIT` por IP para frenar abuso.
    """
    token = AuthService(db).request_password_reset(payload.email)
    if token is not None:
        logger.info("Token de reseteo de contraseña (dev, sin envío de mail): %s", token)
    return ForgotPasswordOut()


@router.post("/password/reset", response_model=ResetPasswordOut)
@limiter.limit(DEFAULT_AUTH_LIMIT)
def reset_password(
    request: Request,  # lo exige el decorador @limiter.limit (slowapi)
    payload: ResetPasswordIn,
    db: Session = Depends(get_session),
) -> ResetPasswordOut:
    """Cambia la contraseña con el token de `/password/forgot`. Token
    ausente/inválido/vencido/ya usado → 400 (ver `AuthService.reset_password`).

    Limitada a `DEFAULT_AUTH_LIMIT` por IP para frenar fuerza bruta sobre el token.
    """
    AuthService(db).reset_password(payload.token, payload.password)
    return ResetPasswordOut()


@router.get("/google/login", status_code=status.HTTP_302_FOUND)
def google_login() -> RedirectResponse:
    """Redirige a Google para iniciar el login OIDC (`state` + PKCE S256).

    El `state`/`code_verifier` viajan firmados en la cookie httpOnly
    `mc_oauth_state` (10 min) — el callback (T-1.8.2) los necesita para
    validar la respuesta de Google y completar el intercambio de código.
    """
    authorization_url, signed_state = build_authorization_redirect()
    response = RedirectResponse(url=authorization_url, status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key=OAUTH_STATE_COOKIE_NAME,
        value=signed_state,
        max_age=OAUTH_STATE_TTL_MINUTES * 60,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        path=OAUTH_STATE_COOKIE_PATH,
    )
    return response


def _google_error_redirect() -> RedirectResponse:
    """Cualquier falla del flujo de Google vuelve al front con `?error=`, no
    con un JSON crudo — esta ruta se llega por navegación de página completa
    (redirección desde Google), no por `fetch`."""
    redirect = RedirectResponse(
        url=f"{settings.frontend_origin}{GOOGLE_CALLBACK_FRONT_PATH}?error=google_auth_failed",
        status_code=status.HTTP_302_FOUND,
    )
    redirect.delete_cookie(key=OAUTH_STATE_COOKIE_NAME, path=OAUTH_STATE_COOKIE_PATH)
    return redirect


@router.get("/google/callback")
def google_callback(request: Request, db: Session = Depends(get_session)) -> RedirectResponse:
    """Callback de Google: valida `state` + `code_verifier` (cookie
    `mc_oauth_state`), canjea el `code` por un `id_token`, lo valida y hace
    login/vinculación/alta (`AuthService.login_with_google`).

    Siempre redirige al front (éxito con el access token en el fragmento de
    la URL + cookie de refresh; error con `?error=google_auth_failed`) —
    nunca devuelve JSON, es una navegación de página completa.
    """
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    state_cookie = request.cookies.get(OAUTH_STATE_COOKIE_NAME)
    if not code or not state or not state_cookie:
        return _google_error_redirect()

    try:
        state_payload = jwt.decode(
            state_cookie, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except jwt.PyJWTError:
        return _google_error_redirect()

    if state_payload.get("state") != state:
        return _google_error_redirect()

    try:
        tokens = exchange_code_for_tokens(code, state_payload["code_verifier"])
        claims = verify_google_id_token(tokens["id_token"])
    except Exception:
        # Cualquier falla del lado de Google (red, respuesta inesperada,
        # id_token inválido) degrada a la misma pantalla de error genérica.
        logger.exception("Fallo intercambiando/validando el id_token de Google")
        return _google_error_redirect()

    try:
        user = AuthService(db).login_with_google(
            sub=claims["sub"],
            email=claims["email"],
            first_name=claims.get("given_name") or "Usuario",
            last_name=claims.get("family_name") or "Google",
        )
    except ForbiddenError:
        return _google_error_redirect()

    redirect = RedirectResponse(
        url=f"{settings.frontend_origin}{GOOGLE_CALLBACK_FRONT_PATH}",
        status_code=status.HTTP_302_FOUND,
    )
    auth_out = issue_tokens(redirect, user)
    redirect.delete_cookie(key=OAUTH_STATE_COOKIE_NAME, path=OAUTH_STATE_COOKIE_PATH)
    redirect.headers["location"] = (
        f"{settings.frontend_origin}{GOOGLE_CALLBACK_FRONT_PATH}"
        f"#access_token={auth_out.access_token}&expires_in={auth_out.expires_in}"
    )
    return redirect


@router.get("/me", response_model=MeOut)
def me(user: User = Depends(get_current_user)) -> MeOut:
    """Datos del usuario logueado (a partir del access token) + su saldo."""
    return MeOut(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        phone=user.phone,
        role=user.role,
        balance=user.balance.balance if user.balance else 0,
    )


__all__ = ["router", "issue_tokens", "set_refresh_cookie", "clear_refresh_cookie"]
