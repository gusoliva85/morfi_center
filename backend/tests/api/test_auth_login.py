import pytest

from app.core.enums import Role, UserStatus
from app.core.security import decode_token, hash_password
from app.models import User
from app.repositories.user_repository import UserRepository

LOGIN = "/api/v1/auth/login"
REGISTER = "/api/v1/auth/register"

EMAIL = "ana@example.com"
PASSWORD = "secreta123"
NEW_ACCOUNT = {
    "first_name": "Ana",
    "last_name": "Pérez",
    "email": EMAIL,
    "password": PASSWORD,
}


@pytest.fixture()
async def registered(client):
    await client.post(REGISTER, json=NEW_ACCOUNT)
    client.cookies.clear()  # el registro ya deja sesión; acá se prueba el login solo


async def test_login_returns_200_with_token_and_user(client, registered):
    response = await client.post(LOGIN, json={"email": EMAIL, "password": PASSWORD})

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 900
    assert body["user"]["email"] == EMAIL
    assert body["user"]["role"] == Role.CUSTOMER.value


async def test_login_sets_the_refresh_cookie(client, registered):
    response = await client.post(LOGIN, json={"email": EMAIL, "password": PASSWORD})

    cookie = response.cookies.get("mc_refresh")
    assert cookie is not None
    assert decode_token(cookie)["type"] == "refresh"

    raw = response.headers["set-cookie"]
    assert "HttpOnly" in raw
    assert "Path=/api/v1/auth" in raw


async def test_the_access_token_carries_the_user_and_role(client, registered):
    response = await client.post(LOGIN, json={"email": EMAIL, "password": PASSWORD})

    body = response.json()
    payload = decode_token(body["access_token"])
    assert payload["sub"] == str(body["user"]["id"])
    assert payload["role"] == Role.CUSTOMER.value
    assert payload["type"] == "access"


async def test_login_accepts_the_email_in_any_case(client, registered):
    response = await client.post(LOGIN, json={"email": "ANA@Example.COM", "password": PASSWORD})

    assert response.status_code == 200


async def test_each_login_issues_a_different_refresh_token(client, registered):
    first = await client.post(LOGIN, json={"email": EMAIL, "password": PASSWORD})
    client.cookies.clear()
    second = await client.post(LOGIN, json={"email": EMAIL, "password": PASSWORD})

    jti_1 = decode_token(first.cookies["mc_refresh"])["jti"]
    jti_2 = decode_token(second.cookies["mc_refresh"])["jti"]
    assert jti_1 != jti_2


async def test_a_wrong_password_returns_401(client, registered):
    response = await client.post(LOGIN, json={"email": EMAIL, "password": "otra-cosa-123"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"
    assert "mc_refresh" not in response.cookies


async def test_an_unknown_email_returns_the_same_401(client, registered):
    unknown = await client.post(LOGIN, json={"email": "nadie@example.com", "password": PASSWORD})
    wrong = await client.post(LOGIN, json={"email": EMAIL, "password": "otra-cosa-123"})

    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json() == wrong.json()  # ni el mensaje delata si el email existe


async def test_a_suspended_user_gets_403(client, registered, session):
    from sqlalchemy import select

    user = session.scalars(select(User)).one()
    user.status = UserStatus.SUSPENDED
    session.flush()

    response = await client.post(LOGIN, json={"email": EMAIL, "password": PASSWORD})

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


async def test_a_missing_field_returns_422_in_the_project_format(client):
    response = await client.post(LOGIN, json={"email": EMAIL})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert response.json()["error"]["details"]["fields"][0]["field"] == "password"


async def test_login_does_not_apply_the_registration_password_policy(client, session):
    """Una cuenta vieja con una contraseña que hoy no pasaría el registro tiene
    que poder entrar igual: el login valida credenciales, no políticas."""
    weak = "corta"
    UserRepository(session).create(
        first_name="Vieja",
        last_name="Cuenta",
        email="vieja@example.com",
        password_hash=hash_password(weak),
    )
    session.flush()

    response = await client.post(LOGIN, json={"email": "vieja@example.com", "password": weak})

    assert response.status_code == 200


async def test_the_response_never_exposes_the_password(client, registered):
    response = await client.post(LOGIN, json={"email": EMAIL, "password": PASSWORD})

    assert PASSWORD not in response.text
    assert "password" not in response.text
