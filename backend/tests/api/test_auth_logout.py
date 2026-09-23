from datetime import timedelta

import jwt
import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.security import create_access_token
from app.core.timezone import now_utc
from app.models import RevokedToken, User

REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
REFRESH = "/api/v1/auth/refresh"
LOGOUT = "/api/v1/auth/logout"

EMAIL = "ana@example.com"
PASSWORD = "secreta123"


@pytest.fixture()
async def logged_in(client):
    await client.post(
        REGISTER,
        json={"first_name": "Ana", "last_name": "Pérez", "email": EMAIL, "password": PASSWORD},
    )
    return client.cookies["mc_refresh"]


async def test_logout_returns_204(client, logged_in):
    response = await client.post(LOGOUT)

    assert response.status_code == 204


async def test_logout_clears_the_cookie(client, logged_in):
    response = await client.post(LOGOUT)

    raw = response.headers["set-cookie"]
    assert "mc_refresh=" in raw
    assert "Max-Age=0" in raw or 'mc_refresh=""' in raw
    assert "Path=/api/v1/auth" in raw


async def test_after_logout_the_refresh_no_longer_works(client, logged_in):
    await client.post(LOGOUT)

    client.cookies.set("mc_refresh", logged_in)  # como si alguien guardó la cookie
    response = await client.post(REFRESH)

    assert response.status_code == 401


async def test_logout_burns_the_token(client, session, logged_in):
    await client.post(LOGOUT)

    revoked = session.scalars(select(RevokedToken)).all()
    assert len(revoked) == 1


async def test_logout_twice_is_still_fine(client, logged_in):
    assert (await client.post(LOGOUT)).status_code == 204

    client.cookies.set("mc_refresh", logged_in)
    assert (await client.post(LOGOUT)).status_code == 204


async def test_logout_without_a_session_is_still_fine(client):
    response = await client.post(LOGOUT)

    assert response.status_code == 204


async def test_logout_with_a_garbage_cookie_is_still_fine(client):
    client.cookies.set("mc_refresh", "esto-no-es-un-token")

    response = await client.post(LOGOUT)

    assert response.status_code == 204


async def test_logout_with_an_expired_cookie_is_still_fine(client, session, logged_in):
    user = session.scalars(select(User)).one()
    expired = jwt.encode(
        {
            "sub": str(user.id),
            "type": "refresh",
            "jti": "vencido-1",
            "exp": now_utc() - timedelta(days=1),
        },
        settings.jwt_secret,
        algorithm="HS256",
    )
    client.cookies.set("mc_refresh", expired)

    response = await client.post(LOGOUT)

    assert response.status_code == 204


async def test_logout_with_an_access_token_as_cookie_is_still_fine(client, session, logged_in):
    user = session.scalars(select(User)).one()
    client.cookies.set("mc_refresh", create_access_token(user))

    response = await client.post(LOGOUT)

    assert response.status_code == 204


async def test_logout_does_not_delete_the_account(client, session, logged_in):
    await client.post(LOGOUT)

    user = session.scalars(select(User)).one()
    assert user.email == EMAIL


async def test_after_logout_the_user_can_log_in_again(client, logged_in):
    await client.post(LOGOUT)

    response = await client.post(LOGIN, json={"email": EMAIL, "password": PASSWORD})

    assert response.status_code == 200
    assert (await client.post(REFRESH)).status_code == 200


async def test_two_simultaneous_logouts_do_not_crash(client, session, logged_in, monkeypatch):
    """Cerrar sesión dos veces a la vez: el segundo choca contra la clave
    primaria al registrar el token quemado, y aun así debe responder 204."""
    await client.post(LOGOUT)

    monkeypatch.setattr(session, "get", lambda model, pk: None)  # simula la carrera
    client.cookies.set("mc_refresh", logged_in)
    response = await client.post(LOGOUT)

    assert response.status_code == 204


async def test_logout_on_one_device_does_not_close_the_other_session(client, logged_in):
    """Cerrar sesión en el celular no debe desloguear la sesión de la compu."""
    other_device = await client.post(LOGIN, json={"email": EMAIL, "password": PASSWORD})
    other_cookie = other_device.cookies["mc_refresh"]

    client.cookies.set("mc_refresh", logged_in)
    await client.post(LOGOUT)

    client.cookies.set("mc_refresh", other_cookie)
    assert (await client.post(REFRESH)).status_code == 200
