from urllib.parse import parse_qs, urlparse

import pytest
from sqlalchemy import func, select

from app.core import oauth as oauth_module
from app.core.config import settings
from app.core.enums import AuthProvider, Role, UserStatus
from app.core.security import decode_token
from app.models import Cart, CustomerBalance, User, UserAuthProvider
from app.repositories.user_repository import UserRepository

CALLBACK = "/api/v1/auth/google/callback"
REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"

GOOGLE_SUB = "google-sub-12345"
GOOGLE_EMAIL = "ana@gmail.com"

CLAIMS = {
    "sub": GOOGLE_SUB,
    "email": GOOGLE_EMAIL,
    "email_verified": True,
    "given_name": "Ana",
    "family_name": "Pérez",
}


@pytest.fixture()
def google_returns(monkeypatch):
    """Simula la vuelta de Google: devuelve el `id_token` ya validado por
    Authlib, que es lo que haría en producción tras canjear el código."""

    def configure(claims: dict | None = CLAIMS, fail: bool = False):
        monkeypatch.setattr(settings, "google_client_id", "id-de-prueba")
        monkeypatch.setattr(settings, "google_client_secret", "secreto-de-prueba")

        async def fake_exchange(request):
            if fail:
                raise ValueError("state inválido")
            return {"access_token": "token-de-google", "userinfo": claims}

        monkeypatch.setattr(oauth_module.oauth.google, "authorize_access_token", fake_exchange)

    return configure


def redirect_query(response) -> dict[str, list[str]]:
    return parse_qs(urlparse(response.headers["location"]).query)


# ---------- camino 1: cuenta nueva ----------


async def test_a_new_google_user_gets_an_account(client, session, google_returns):
    google_returns()

    response = await client.get(CALLBACK)

    assert response.status_code in (302, 307)
    user = session.scalars(select(User)).one()
    assert user.email == GOOGLE_EMAIL
    assert user.role == Role.CUSTOMER
    assert user.first_name == "Ana"
    assert user.last_name == "Pérez"


async def test_the_new_account_has_no_password(client, session, google_returns):
    """Entra solo con Google hasta que use "olvidé mi contraseña"."""
    google_returns()

    await client.get(CALLBACK)

    assert session.scalars(select(User)).one().password_hash is None


async def test_the_new_account_gets_its_cart_and_balance(client, session, google_returns):
    google_returns()

    await client.get(CALLBACK)

    assert session.scalars(select(Cart)).all() != []
    assert session.scalars(select(CustomerBalance)).one().balance == 0


async def test_the_google_provider_is_linked(client, session, google_returns):
    google_returns()

    await client.get(CALLBACK)

    provider = session.scalars(select(UserAuthProvider)).one()
    assert provider.provider == AuthProvider.GOOGLE
    assert provider.provider_uid == GOOGLE_SUB


async def test_it_leaves_the_session_cookie_and_goes_to_the_front(client, google_returns):
    google_returns()

    response = await client.get(CALLBACK)

    assert decode_token(response.cookies["mc_refresh"])["type"] == "refresh"
    assert response.headers["location"].startswith(settings.frontend_origin)


async def test_it_does_not_put_the_token_in_the_url(client, google_returns):
    """Un token en la URL queda en el historial, en los logs y en el `Referer`."""
    google_returns()

    response = await client.get(CALLBACK)

    assert "access_token" not in response.headers["location"]
    assert "token" not in redirect_query(response)


async def test_the_email_is_normalized(client, session, google_returns):
    google_returns({**CLAIMS, "email": "  ANA@Gmail.COM "})

    await client.get(CALLBACK)

    assert session.scalars(select(User)).one().email == "ana@gmail.com"


async def test_it_works_when_google_omits_the_names(client, session, google_returns):
    google_returns({"sub": GOOGLE_SUB, "email": GOOGLE_EMAIL, "email_verified": True})

    response = await client.get(CALLBACK)

    assert response.status_code in (302, 307)
    user = session.scalars(select(User)).one()
    assert user.first_name  # algo mostrable, no vacío
    assert user.last_name


# ---------- camino 2: ya existe cuenta con ese email ----------


async def test_it_links_google_to_an_existing_local_account(client, session, google_returns):
    """Si no vinculara, quedarían dos cuentas separadas de la misma persona."""
    await client.post(
        REGISTER,
        json={
            "first_name": "Ana",
            "last_name": "Pérez",
            "email": GOOGLE_EMAIL,
            "password": "secreta123",
        },
    )
    google_returns()

    await client.get(CALLBACK)

    assert session.scalar(select(func.count()).select_from(User)) == 1
    providers = {p.provider for p in session.scalars(select(UserAuthProvider)).all()}
    assert providers == {AuthProvider.LOCAL, AuthProvider.GOOGLE}


async def test_linking_keeps_the_local_password_working(client, session, google_returns):
    await client.post(
        REGISTER,
        json={
            "first_name": "Ana",
            "last_name": "Pérez",
            "email": GOOGLE_EMAIL,
            "password": "secreta123",
        },
    )
    google_returns()
    await client.get(CALLBACK)
    client.cookies.clear()

    response = await client.post(LOGIN, json={"email": GOOGLE_EMAIL, "password": "secreta123"})

    assert response.status_code == 200


# ---------- camino 3: ya entró antes con Google ----------


async def test_a_returning_google_user_logs_in_without_duplicating_anything(
    client, session, google_returns
):
    google_returns()
    await client.get(CALLBACK)
    client.cookies.clear()

    response = await client.get(CALLBACK)

    assert response.status_code in (302, 307)
    assert session.scalar(select(func.count()).select_from(User)) == 1
    assert session.scalar(select(func.count()).select_from(UserAuthProvider)) == 1


async def test_it_recognizes_the_account_even_if_the_email_changed_at_google(
    client, session, google_returns
):
    """La identidad es el `sub` de Google, no el email: si la persona cambia su
    email en Google, sigue siendo la misma cuenta."""
    google_returns()
    await client.get(CALLBACK)

    google_returns({**CLAIMS, "email": "ana.nueva@gmail.com"})
    await client.get(CALLBACK)

    assert session.scalar(select(func.count()).select_from(User)) == 1


# ---------- errores ----------


async def test_a_failed_exchange_returns_to_the_front_with_an_error(
    client, session, google_returns
):
    google_returns(fail=True)

    response = await client.get(CALLBACK)

    assert response.status_code in (302, 307)
    assert redirect_query(response)["auth_error"] == ["google"]
    assert session.scalars(select(User)).all() == []


async def test_an_unverified_email_is_rejected(client, session, google_returns):
    """Vincular con un email sin confirmar permitiría reclamar la cuenta de otro."""
    google_returns({**CLAIMS, "email_verified": False})

    response = await client.get(CALLBACK)

    assert redirect_query(response)["auth_error"] == ["google_email_unverified"]
    assert session.scalars(select(User)).all() == []


@pytest.mark.parametrize("missing", ["email", "sub"])
async def test_missing_claims_are_rejected(client, session, google_returns, missing):
    claims = {k: v for k, v in CLAIMS.items() if k != missing}
    google_returns(claims)

    response = await client.get(CALLBACK)

    assert redirect_query(response)["auth_error"] == ["google"]
    assert session.scalars(select(User)).all() == []


async def test_a_suspended_user_cannot_enter_with_google(client, session, google_returns):
    google_returns()
    await client.get(CALLBACK)
    session.scalars(select(User)).one().status = UserStatus.SUSPENDED
    session.flush()
    client.cookies.clear()

    response = await client.get(CALLBACK)

    assert redirect_query(response)["auth_error"] == ["account_not_active"]
    assert "mc_refresh" not in response.cookies


async def test_without_credentials_it_is_unavailable(client, monkeypatch):
    monkeypatch.setattr(settings, "google_client_id", "")
    monkeypatch.setattr(settings, "google_client_secret", "")

    response = await client.get(CALLBACK)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "SERVICE_UNAVAILABLE"


async def test_a_suspended_local_account_is_not_linked_by_google(client, session, google_returns):
    """Un suspendido no debería poder entrar dando la vuelta por Google."""
    user = UserRepository(session).create(
        first_name="Ana",
        last_name="Pérez",
        email=GOOGLE_EMAIL,
        password_hash="hash",
        status=UserStatus.SUSPENDED,
    )
    session.flush()
    google_returns()

    response = await client.get(CALLBACK)

    assert redirect_query(response)["auth_error"] == ["account_not_active"]
    assert "mc_refresh" not in response.cookies
    assert session.get(User, user.id).status == UserStatus.SUSPENDED
