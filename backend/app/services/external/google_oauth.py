"""Cliente OAuth2/OIDC de Google con Authlib (Tema 1.8).

``build_authorization_redirect`` arma la URL de autorización con ``state`` +
PKCE (S256) para ``GET /auth/google/login``. El ``state`` y el
``code_verifier`` viajan firmados en una cookie httpOnly de corta duración
(``mc_oauth_state``) para que el callback (T-1.8.2) pueda recuperarlos y
validar que el ``state`` no fue alterado — es la forma de pasar ese dato
entre el ``/login`` y el ``/callback`` sin sesión de servidor (el proyecto
no usa `Starlette SessionMiddleware`, solo JWT).

``exchange_code_for_tokens`` + ``verify_google_id_token`` son los dos pasos
del callback (T-1.8.2): canjear el ``code`` por un ``id_token`` y validar su
firma (RS256, JWKS de Google) antes de confiar en sus claims.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from authlib.common.security import generate_token
from authlib.integrations.httpx_client import OAuth2Client
from jwt import PyJWKClient

from app.core.config import settings

GOOGLE_AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_JWKS_URI = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ISSUERS = ("https://accounts.google.com", "accounts.google.com")
GOOGLE_SCOPE = "openid email profile"

OAUTH_STATE_COOKIE_NAME = "mc_oauth_state"
OAUTH_STATE_COOKIE_PATH = f"{settings.api_prefix}/auth/google"
OAUTH_STATE_TTL_MINUTES = 10

# Un solo `PyJWKClient` para todo el proceso: cachea las claves públicas de
# Google (`cache_keys=True`) para no pegarle a `GOOGLE_JWKS_URI` en cada login.
_jwks_client: PyJWKClient | None = None


class InvalidGoogleTokenError(Exception):
    """El `id_token` de Google no es válido: firma, issuer, audience o vigencia."""


def _build_client() -> OAuth2Client:
    return OAuth2Client(
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        redirect_uri=settings.google_redirect_uri,
        scope=GOOGLE_SCOPE,
        code_challenge_method="S256",
    )


def build_authorization_redirect() -> tuple[str, str]:
    """Arma la URL de autorización de Google y el valor firmado que va en la
    cookie `mc_oauth_state`.

    :return: ``(authorization_url, signed_state_cookie_value)``.
    """
    client = _build_client()
    code_verifier = generate_token(64)
    authorization_url, state = client.create_authorization_url(
        GOOGLE_AUTHORIZATION_ENDPOINT, code_verifier=code_verifier
    )

    payload = {
        "state": state,
        "code_verifier": code_verifier,
        "exp": int((datetime.now(UTC) + timedelta(minutes=OAUTH_STATE_TTL_MINUTES)).timestamp()),
    }
    signed_cookie_value = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return authorization_url, signed_cookie_value


def exchange_code_for_tokens(code: str, code_verifier: str) -> dict[str, Any]:
    """Canjea el `code` de la respuesta de Google por sus tokens (incluye
    `id_token`). Hace una llamada HTTP real al token endpoint de Google."""
    client = _build_client()
    return dict(client.fetch_token(GOOGLE_TOKEN_ENDPOINT, code=code, code_verifier=code_verifier))


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(GOOGLE_JWKS_URI, cache_keys=True)
    return _jwks_client


def verify_google_id_token(id_token: str) -> dict[str, Any]:
    """Valida la firma (RS256, JWKS de Google), el issuer, el audience
    (`GOOGLE_CLIENT_ID`) y la vigencia del `id_token`. Devuelve sus claims
    (`sub`, `email`, `given_name`, `family_name`, ...).

    :raises InvalidGoogleTokenError: si cualquiera de esas validaciones falla.
    """
    try:
        signing_key = _get_jwks_client().get_signing_key_from_jwt(id_token)
        claims: dict[str, Any] = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.google_client_id,
            issuer=list(GOOGLE_ISSUERS),
        )
    except jwt.PyJWTError as exc:
        raise InvalidGoogleTokenError("El id_token de Google no es válido.") from exc
    return claims


__all__ = [
    "GOOGLE_AUTHORIZATION_ENDPOINT",
    "GOOGLE_TOKEN_ENDPOINT",
    "GOOGLE_JWKS_URI",
    "GOOGLE_ISSUERS",
    "GOOGLE_SCOPE",
    "OAUTH_STATE_COOKIE_NAME",
    "OAUTH_STATE_COOKIE_PATH",
    "OAUTH_STATE_TTL_MINUTES",
    "InvalidGoogleTokenError",
    "build_authorization_redirect",
    "exchange_code_for_tokens",
    "verify_google_id_token",
]
