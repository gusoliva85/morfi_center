import pytest
from sqlalchemy import select

from app.core.enums import Role, UserStatus
from app.core.security import create_access_token, hash_password
from app.models import User
from app.repositories.user_repository import UserRepository

ME = "/api/v1/auth/me"
REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
REFRESH = "/api/v1/auth/refresh"

ACCOUNT = {
    "first_name": "Ana",
    "last_name": "Pérez",
    "email": "ana@example.com",
    "password": "secreta123",
    "phone": "1155551234",
}


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
async def customer_token(client):
    registered = await client.post(REGISTER, json=ACCOUNT)
    return registered.json()["access_token"]


async def test_me_returns_the_current_user(client, customer_token):
    response = await client.get(ME, headers=auth(customer_token))

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == ACCOUNT["email"]
    assert body["first_name"] == "Ana"
    assert body["last_name"] == "Pérez"
    assert body["phone"] == "1155551234"
    assert body["role"] == Role.CUSTOMER.value
    assert body["id"] > 0


async def test_a_new_customer_has_zero_balance(client, customer_token):
    response = await client.get(ME, headers=auth(customer_token))

    assert response.json()["balance"] == 0


async def test_the_balance_is_reported_in_cents(client, session, customer_token):
    session.scalars(select(User)).one().balance.balance = 150000  # $1.500
    session.flush()

    response = await client.get(ME, headers=auth(customer_token))

    assert response.json()["balance"] == 150000


async def test_staff_without_a_balance_row_reports_zero(client, session):
    """Un ADMIN no tiene fila de saldo: debe devolver 0, no reventar."""
    admin = UserRepository(session).create(
        first_name="Admin",
        last_name="Morfi",
        email="admin@example.com",
        password_hash=hash_password("secreta123"),
        role=Role.ADMIN,
    )
    session.flush()

    response = await client.get(ME, headers=auth(create_access_token(admin)))

    assert response.status_code == 200
    assert response.json()["balance"] == 0
    assert response.json()["role"] == Role.ADMIN.value


async def test_me_never_exposes_the_password_hash(client, customer_token):
    response = await client.get(ME, headers=auth(customer_token))

    assert "password" not in response.text
    assert set(response.json()) == {
        "id",
        "first_name",
        "last_name",
        "email",
        "phone",
        "role",
        "balance",
    }


async def test_without_a_token_it_is_401(client):
    response = await client.get(ME)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"


async def test_a_suspended_user_gets_403(client, session, customer_token):
    session.scalars(select(User)).one().status = UserStatus.SUSPENDED
    session.flush()

    response = await client.get(ME, headers=auth(customer_token))

    assert response.status_code == 403


async def test_the_token_from_login_also_works(client, customer_token):
    logged_in = await client.post(
        LOGIN, json={"email": ACCOUNT["email"], "password": ACCOUNT["password"]}
    )

    response = await client.get(ME, headers=auth(logged_in.json()["access_token"]))

    assert response.status_code == 200
    assert response.json()["email"] == ACCOUNT["email"]


async def test_the_token_from_refresh_also_works(client, customer_token):
    """Recorrido real del front: recarga la página, renueva la sesión con la
    cookie y con ese token nuevo pregunta quién es."""
    refreshed = await client.post(REFRESH)

    response = await client.get(ME, headers=auth(refreshed.json()["access_token"]))

    assert response.status_code == 200
    assert response.json()["email"] == ACCOUNT["email"]


async def test_each_user_only_sees_their_own_data(client, session, customer_token):
    other = UserRepository(session).create(
        first_name="Juan",
        last_name="Gómez",
        email="juan@example.com",
        password_hash=hash_password("secreta123"),
    )
    session.flush()

    mine = await client.get(ME, headers=auth(customer_token))
    theirs = await client.get(ME, headers=auth(create_access_token(other)))

    assert mine.json()["email"] == ACCOUNT["email"]
    assert theirs.json()["email"] == "juan@example.com"
