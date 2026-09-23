import re
from datetime import timedelta

import jwt
import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.enums import AuthProvider, UserStatus
from app.core.security import create_password_reset_token, hash_password, verify_password
from app.core.timezone import now_utc
from app.models import RevokedToken, User, UserAuthProvider
from app.repositories.user_repository import UserRepository

FORGOT = "/api/v1/auth/password/forgot"
RESET = "/api/v1/auth/password/reset"
LOGIN = "/api/v1/auth/login"
REGISTER = "/api/v1/auth/register"

EMAIL = "ana@example.com"
OLD_PASSWORD = "secreta123"
NEW_PASSWORD = "flamante456"

ACCOUNT = {"first_name": "Ana", "last_name": "Pérez", "email": EMAIL, "password": OLD_PASSWORD}


@pytest.fixture()
async def registered(client):
    await client.post(REGISTER, json=ACCOUNT)
    client.cookies.clear()


def token_from_logs(caplog) -> str:
    """El link se loguea en el servidor (todavía no hay servicio de mail)."""
    match = re.search(r"token=([\w\-.]+)", caplog.text)
    assert match, f"no se logueó ningún link: {caplog.text}"
    return match.group(1)


# ---------- pedir el link ----------


async def test_asking_for_a_link_answers_ok(client, registered):
    response = await client.post(FORGOT, json={"email": EMAIL})

    assert response.status_code == 200
    assert response.json()["message"]


async def test_an_unknown_email_gets_the_exact_same_answer(client, registered):
    """Si la respuesta cambiara, serviría para averiguar qué emails existen."""
    known = await client.post(FORGOT, json={"email": EMAIL})
    unknown = await client.post(FORGOT, json={"email": "nadie@example.com"})

    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()


async def test_a_link_is_generated_for_a_real_account(client, registered, caplog):
    with caplog.at_level("WARNING"):
        await client.post(FORGOT, json={"email": EMAIL})

    assert token_from_logs(caplog)


async def test_no_link_is_generated_for_an_unknown_email(client, registered, caplog):
    with caplog.at_level("WARNING"):
        await client.post(FORGOT, json={"email": "nadie@example.com"})

    assert "token=" not in caplog.text


async def test_no_link_is_generated_for_a_suspended_account(client, session, registered, caplog):
    session.scalars(select(User)).one().status = UserStatus.SUSPENDED
    session.flush()

    with caplog.at_level("WARNING"):
        response = await client.post(FORGOT, json={"email": EMAIL})

    assert response.status_code == 200  # no se delata
    assert "token=" not in caplog.text


async def test_the_email_is_matched_ignoring_case(client, registered, caplog):
    with caplog.at_level("WARNING"):
        await client.post(FORGOT, json={"email": "ANA@Example.COM"})

    assert token_from_logs(caplog)


# ---------- usar el link ----------


async def test_the_password_changes_and_the_new_one_works(client, registered, caplog):
    with caplog.at_level("WARNING"):
        await client.post(FORGOT, json={"email": EMAIL})
    token = token_from_logs(caplog)

    response = await client.post(RESET, json={"token": token, "password": NEW_PASSWORD})

    assert response.status_code == 200
    login = await client.post(LOGIN, json={"email": EMAIL, "password": NEW_PASSWORD})
    assert login.status_code == 200


async def test_the_old_password_stops_working(client, registered, caplog):
    with caplog.at_level("WARNING"):
        await client.post(FORGOT, json={"email": EMAIL})
    await client.post(RESET, json={"token": token_from_logs(caplog), "password": NEW_PASSWORD})

    response = await client.post(LOGIN, json={"email": EMAIL, "password": OLD_PASSWORD})

    assert response.status_code == 401


async def test_the_new_password_is_stored_hashed(client, session, registered, caplog):
    with caplog.at_level("WARNING"):
        await client.post(FORGOT, json={"email": EMAIL})
    await client.post(RESET, json={"token": token_from_logs(caplog), "password": NEW_PASSWORD})

    session.expire_all()
    user = session.scalars(select(User)).one()
    assert user.password_hash != NEW_PASSWORD
    assert verify_password(NEW_PASSWORD, user.password_hash)


async def test_the_link_works_only_once(client, registered, caplog):
    with caplog.at_level("WARNING"):
        await client.post(FORGOT, json={"email": EMAIL})
    token = token_from_logs(caplog)
    await client.post(RESET, json={"token": token, "password": NEW_PASSWORD})

    response = await client.post(RESET, json={"token": token, "password": "otra-mas-789"})

    assert response.status_code == 401


async def test_an_older_link_dies_when_the_password_changes(client, registered, caplog):
    """Dos links pedidos y uno usado: el otro (por ejemplo, de un mail viejo
    reenviado) no debe servir para volver a cambiar la contraseña."""
    with caplog.at_level("WARNING"):
        await client.post(FORGOT, json={"email": EMAIL})
        first = token_from_logs(caplog)
        caplog.clear()
        await client.post(FORGOT, json={"email": EMAIL})
        second = token_from_logs(caplog)

    assert first != second
    await client.post(RESET, json={"token": second, "password": NEW_PASSWORD})

    response = await client.post(RESET, json={"token": first, "password": "otra-mas-789"})
    assert response.status_code == 401


async def test_using_the_link_burns_it_in_the_database(client, session, registered, caplog):
    with caplog.at_level("WARNING"):
        await client.post(FORGOT, json={"email": EMAIL})
    await client.post(RESET, json={"token": token_from_logs(caplog), "password": NEW_PASSWORD})

    assert len(session.scalars(select(RevokedToken)).all()) == 1


async def test_a_google_only_account_can_set_a_password(client, session, caplog):
    """Una cuenta sin contraseña (solo Google) usa este flujo para tener una."""
    user = UserRepository(session).create(
        first_name="Juan", last_name="Gómez", email="juan@example.com", password_hash=None
    )
    UserRepository(session).link_provider(user, AuthProvider.GOOGLE, provider_uid="sub-1")
    session.flush()

    with caplog.at_level("WARNING"):
        await client.post(FORGOT, json={"email": "juan@example.com"})
    await client.post(RESET, json={"token": token_from_logs(caplog), "password": NEW_PASSWORD})

    login = await client.post(LOGIN, json={"email": "juan@example.com", "password": NEW_PASSWORD})
    assert login.status_code == 200
    providers = {p.provider for p in session.scalars(select(UserAuthProvider)).all()}
    assert providers == {AuthProvider.GOOGLE, AuthProvider.LOCAL}


# ---------- links inválidos ----------


async def test_a_garbage_token_is_rejected(client, registered):
    response = await client.post(RESET, json={"token": "no-es-un-token", "password": NEW_PASSWORD})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"


async def test_an_expired_token_is_rejected(client, session, registered):
    user = session.scalars(select(User)).one()
    expired = jwt.encode(
        {
            "sub": str(user.id),
            "type": "password_reset",
            "jti": "vencido-1",
            "pwd": "loquesea",
            "exp": now_utc() - timedelta(minutes=1),
        },
        settings.jwt_secret,
        algorithm="HS256",
    )

    response = await client.post(RESET, json={"token": expired, "password": NEW_PASSWORD})

    assert response.status_code == 401


async def test_a_token_signed_with_another_secret_is_rejected(client, session, registered):
    user = session.scalars(select(User)).one()
    forged = jwt.encode(
        {
            "sub": str(user.id),
            "type": "password_reset",
            "jti": "falso-1",
            "pwd": "loquesea",
            "exp": now_utc() + timedelta(minutes=30),
        },
        "otro-secreto-cualquiera",
        algorithm="HS256",
    )

    response = await client.post(RESET, json={"token": forged, "password": NEW_PASSWORD})

    assert response.status_code == 401


async def test_a_session_token_cannot_be_used_as_a_reset_link(client, registered):
    """Un access o un refresh no deben servir para cambiar la contraseña."""
    login = await client.post(LOGIN, json={"email": EMAIL, "password": OLD_PASSWORD})

    response = await client.post(
        RESET, json={"token": login.json()["access_token"], "password": NEW_PASSWORD}
    )

    assert response.status_code == 401


async def test_a_suspended_user_cannot_reset(client, session, registered):
    user = session.scalars(select(User)).one()
    token = create_password_reset_token(user, user.password_hash)
    user.status = UserStatus.SUSPENDED
    session.flush()

    response = await client.post(RESET, json={"token": token, "password": NEW_PASSWORD})

    assert response.status_code == 401


async def test_a_weak_new_password_is_rejected(client, session, registered, caplog):
    with caplog.at_level("WARNING"):
        await client.post(FORGOT, json={"email": EMAIL})
    token = token_from_logs(caplog)

    response = await client.post(RESET, json={"token": token, "password": "corta"})

    assert response.status_code == 422
    assert "password" in [f["field"] for f in response.json()["error"]["details"]["fields"]]
    login = await client.post(LOGIN, json={"email": EMAIL, "password": OLD_PASSWORD})
    assert login.status_code == 200  # la vieja sigue valiendo


async def test_a_rejected_reset_does_not_burn_the_link(client, registered, caplog):
    with caplog.at_level("WARNING"):
        await client.post(FORGOT, json={"email": EMAIL})
    token = token_from_logs(caplog)
    await client.post(RESET, json={"token": token, "password": "corta"})

    response = await client.post(RESET, json={"token": token, "password": NEW_PASSWORD})

    assert response.status_code == 200


async def test_a_token_of_a_deleted_user_is_rejected(client, session, registered):
    user = session.scalars(select(User)).one()
    token = create_password_reset_token(user, user.password_hash)
    session.delete(user)
    session.flush()

    response = await client.post(RESET, json={"token": token, "password": NEW_PASSWORD})

    assert response.status_code == 401


# ---------- límite de intentos ----------


async def test_both_endpoints_are_rate_limited(client, registered):
    for _ in range(11):
        forgot = await client.post(FORGOT, json={"email": EMAIL})
    for _ in range(11):
        reset = await client.post(RESET, json={"token": "cualquiera", "password": NEW_PASSWORD})

    assert forgot.status_code == 429
    assert reset.status_code == 429


async def test_the_password_hash_never_leaks_in_the_response(client, registered, caplog):
    with caplog.at_level("WARNING"):
        await client.post(FORGOT, json={"email": EMAIL})
    response = await client.post(
        RESET, json={"token": token_from_logs(caplog), "password": NEW_PASSWORD}
    )

    assert "hash" not in response.text
    assert NEW_PASSWORD not in response.text


async def test_the_reset_link_does_not_depend_on_a_previous_session(client, session):
    """Quien olvidó la contraseña justamente no tiene sesión."""
    user = UserRepository(session).create(
        first_name="Sin",
        last_name="Sesion",
        email="sin@example.com",
        password_hash=hash_password(OLD_PASSWORD),
    )
    session.flush()
    token = create_password_reset_token(user, user.password_hash)

    response = await client.post(RESET, json={"token": token, "password": NEW_PASSWORD})

    assert response.status_code == 200
