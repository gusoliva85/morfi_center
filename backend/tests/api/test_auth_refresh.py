from datetime import timedelta

import jwt
import pytest
from sqlalchemy import func, select

from app.core.config import settings
from app.core.enums import UserStatus
from app.core.security import create_access_token, decode_token
from app.core.timezone import now_utc
from app.models import RevokedToken, User

REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
REFRESH = "/api/v1/auth/refresh"

EMAIL = "ana@example.com"
PASSWORD = "secreta123"


@pytest.fixture()
async def logged_in(client):
    """Deja al cliente con la cookie de refresh puesta, como un navegador."""
    await client.post(
        REGISTER,
        json={"first_name": "Ana", "last_name": "Pérez", "email": EMAIL, "password": PASSWORD},
    )
    return client.cookies["mc_refresh"]


async def test_refresh_returns_a_new_access_token(client, logged_in):
    response = await client.post(REFRESH)

    assert response.status_code == 200
    body = response.json()
    assert decode_token(body["access_token"])["type"] == "access"
    assert body["user"]["email"] == EMAIL
    assert body["expires_in"] == 900


async def test_refresh_rotates_the_cookie(client, logged_in):
    response = await client.post(REFRESH)

    new_cookie = response.cookies["mc_refresh"]
    assert new_cookie != logged_in
    assert decode_token(new_cookie)["jti"] != decode_token(logged_in)["jti"]


async def test_the_old_refresh_stops_working_after_rotation(client, logged_in):
    await client.post(REFRESH)

    # Se vuelve a mandar el token viejo a mano, como haría un atacante que lo robó.
    client.cookies.set("mc_refresh", logged_in)
    response = await client.post(REFRESH)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"


async def test_the_new_refresh_keeps_working(client, logged_in):
    await client.post(REFRESH)

    response = await client.post(REFRESH)

    assert response.status_code == 200


async def test_refresh_without_cookie_returns_401(client):
    response = await client.post(REFRESH)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"


async def test_an_access_token_cannot_be_used_as_refresh(client, session, logged_in):
    user = session.scalars(select(User)).one()
    client.cookies.set("mc_refresh", create_access_token(user))

    response = await client.post(REFRESH)

    assert response.status_code == 401


async def test_an_expired_refresh_returns_401(client, session, logged_in):
    user = session.scalars(select(User)).one()
    expired = jwt.encode(
        {
            "sub": str(user.id),
            "type": "refresh",
            "jti": "vencido-1",
            "iat": now_utc() - timedelta(days=8),
            "exp": now_utc() - timedelta(days=1),
        },
        settings.jwt_secret,
        algorithm="HS256",
    )
    client.cookies.set("mc_refresh", expired)

    response = await client.post(REFRESH)

    assert response.status_code == 401


async def test_a_tampered_refresh_returns_401(client, logged_in):
    tampered = logged_in[:-1] + ("A" if logged_in[-1] != "A" else "B")
    client.cookies.set("mc_refresh", tampered)

    response = await client.post(REFRESH)

    assert response.status_code == 401


async def test_a_refresh_signed_with_another_secret_returns_401(client, session, logged_in):
    user = session.scalars(select(User)).one()
    forged = jwt.encode(
        {
            "sub": str(user.id),
            "type": "refresh",
            "jti": "falsificado-1",
            "exp": now_utc() + timedelta(days=7),
        },
        "otro-secreto-cualquiera",
        algorithm="HS256",
    )
    client.cookies.set("mc_refresh", forged)

    response = await client.post(REFRESH)

    assert response.status_code == 401


async def test_a_suspended_user_cannot_refresh(client, session, logged_in):
    user = session.scalars(select(User)).one()
    user.status = UserStatus.SUSPENDED
    session.flush()

    response = await client.post(REFRESH)

    assert response.status_code == 403


async def test_rotation_records_the_burnt_token(client, session, logged_in):
    await client.post(REFRESH)

    revoked = session.scalars(select(RevokedToken)).all()
    assert [r.jti for r in revoked] == [decode_token(logged_in)["jti"]]


async def test_expired_revocations_are_cleaned_up(client, session, logged_in):
    """La tabla no debe crecer para siempre: las revocaciones de tokens ya
    vencidos no sirven de nada (el token falla igual) y se borran."""
    session.add(RevokedToken(jti="viejo-vencido", expires_at=now_utc() - timedelta(days=1)))
    session.add(RevokedToken(jti="todavia-vigente", expires_at=now_utc() + timedelta(days=3)))
    session.flush()

    await client.post(REFRESH)

    jtis = {r.jti for r in session.scalars(select(RevokedToken)).all()}
    assert "viejo-vencido" not in jtis
    assert "todavia-vigente" in jtis


async def test_login_after_a_burnt_refresh_works_again(client, logged_in):
    """Quemar el refresh no bloquea la cuenta: se puede volver a loguear."""
    await client.post(REFRESH)
    client.cookies.set("mc_refresh", logged_in)
    assert (await client.post(REFRESH)).status_code == 401

    client.cookies.clear()
    response = await client.post(LOGIN, json={"email": EMAIL, "password": PASSWORD})

    assert response.status_code == 200


async def test_two_sessions_can_refresh_independently(client, session, logged_in):
    """Dos dispositivos: rotar el refresh de uno no debe desloguear al otro."""
    second = await client.post(LOGIN, json={"email": EMAIL, "password": PASSWORD})
    second_cookie = second.cookies["mc_refresh"]

    client.cookies.set("mc_refresh", logged_in)
    assert (await client.post(REFRESH)).status_code == 200

    client.cookies.set("mc_refresh", second_cookie)
    assert (await client.post(REFRESH)).status_code == 200

    assert session.scalar(select(func.count()).select_from(RevokedToken)) == 2
