from urllib.parse import parse_qs, urlparse

import pytest

from app.core import oauth as oauth_module
from app.core.config import settings

GOOGLE_LOGIN = "/api/v1/auth/google/login"


@pytest.fixture()
def google_configured(monkeypatch):
    """Credenciales de prueba: el flujo se arma igual, sin llamar a Google."""
    monkeypatch.setattr(settings, "google_client_id", "id-de-prueba.apps.googleusercontent.com")
    monkeypatch.setattr(settings, "google_client_secret", "secreto-de-prueba")
    monkeypatch.setattr(
        settings, "google_redirect_uri", "http://testserver/api/v1/auth/google/callback"
    )
    client = oauth_module.oauth.google
    monkeypatch.setattr(client, "client_id", settings.google_client_id)
    monkeypatch.setattr(client, "client_secret", settings.google_client_secret)


async def redirect_params(client) -> dict[str, list[str]]:
    response = await client.get(GOOGLE_LOGIN)
    assert response.status_code in (302, 307)
    return parse_qs(urlparse(response.headers["location"]).query)


async def test_it_redirects_to_google(client, google_configured):
    response = await client.get(GOOGLE_LOGIN)

    location = urlparse(response.headers["location"])
    assert response.status_code in (302, 307)
    assert location.hostname == "accounts.google.com"


async def test_it_asks_for_an_authorization_code_with_our_client_id(client, google_configured):
    params = await redirect_params(client)

    assert params["response_type"] == ["code"]
    assert params["client_id"] == [settings.google_client_id]
    assert params["redirect_uri"] == [settings.google_redirect_uri]


async def test_it_asks_for_the_identity_scopes(client, google_configured):
    params = await redirect_params(client)

    scope = params["scope"][0].split()
    assert "openid" in scope
    assert "email" in scope
    assert "profile" in scope


async def test_it_sends_a_state_to_detect_a_forged_return(client, google_configured):
    """Sin `state`, alguien podría hacerle completar a la víctima un login con
    una cuenta ajena (CSRF sobre el login)."""
    params = await redirect_params(client)

    assert params["state"][0]


async def test_it_uses_pkce(client, google_configured):
    """Con PKCE, el código que vuelve de Google no sirve para nadie que no tenga
    el verificador que quedó guardado de este lado."""
    params = await redirect_params(client)

    assert params["code_challenge_method"] == ["S256"]
    assert params["code_challenge"][0]


async def test_the_state_and_the_verifier_are_kept_in_a_signed_cookie(client, google_configured):
    response = await client.get(GOOGLE_LOGIN)

    assert "mc_oauth" in response.cookies
    # Starlette escribe los atributos en minúscula (la especificación los define
    # sin distinguir mayúsculas), a diferencia del set_cookie de FastAPI.
    raw = response.headers["set-cookie"].lower()
    assert "httponly" in raw
    assert "samesite=lax" in raw  # tiene que sobrevivir la vuelta desde Google


async def test_two_logins_use_different_states(client, google_configured):
    first = await redirect_params(client)
    second = await redirect_params(client)

    assert first["state"] != second["state"]
    assert first["code_challenge"] != second["code_challenge"]


async def test_without_credentials_it_answers_that_it_is_unavailable(client, monkeypatch):
    """Hoy producción no tiene credenciales de Google: el usuario tiene que
    recibir un mensaje claro, no un error interno."""
    monkeypatch.setattr(settings, "google_client_id", "")
    monkeypatch.setattr(settings, "google_client_secret", "")

    response = await client.get(GOOGLE_LOGIN)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "SERVICE_UNAVAILABLE"
    assert "contraseña" in response.json()["error"]["message"]


async def test_it_does_not_require_a_session(client, google_configured):
    """Es el punto de entrada de alguien que todavía no tiene cuenta."""
    response = await client.get(GOOGLE_LOGIN)

    assert response.status_code in (302, 307)
