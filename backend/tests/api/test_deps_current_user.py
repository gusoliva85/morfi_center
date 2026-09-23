from datetime import timedelta

import jwt
import pytest
from sqlalchemy import select

from app.api.deps import CurrentUser
from app.core.config import settings
from app.core.enums import Role, UserStatus
from app.core.security import create_access_token, create_refresh_token, hash_password
from app.core.timezone import now_utc
from app.main import app
from app.models import User
from app.repositories.user_repository import UserRepository

REGISTER = "/api/v1/auth/register"
PROTECTED = "/api/v1/_test/protegido"

ACCOUNT = {
    "first_name": "Ana",
    "last_name": "Pérez",
    "email": "ana@example.com",
    "password": "secreta123",
}


@pytest.fixture(autouse=True)
def protected_route():
    """Endpoint mínimo que solo existe para probar la dependencia en sí,
    sin depender de `/auth/me` (que llega en T-1.5.3)."""

    @app.get(PROTECTED)
    def _protegido(user: CurrentUser) -> dict:
        return {"id": user.id, "email": user.email, "role": user.role}

    yield
    app.router.routes = [r for r in app.router.routes if getattr(r, "path", "") != PROTECTED]


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_a_valid_token_identifies_the_user(client):
    registered = await client.post(REGISTER, json=ACCOUNT)
    token = registered.json()["access_token"]

    response = await client.get(PROTECTED, headers=auth(token))

    assert response.status_code == 200
    assert response.json()["email"] == ACCOUNT["email"]
    assert response.json()["role"] == Role.CUSTOMER.value


async def test_without_a_token_it_is_401(client):
    response = await client.get(PROTECTED)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"


async def test_a_header_without_the_bearer_scheme_is_401(client):
    registered = await client.post(REGISTER, json=ACCOUNT)
    token = registered.json()["access_token"]

    response = await client.get(PROTECTED, headers={"Authorization": token})

    assert response.status_code == 401


async def test_an_empty_bearer_is_401(client):
    response = await client.get(PROTECTED, headers={"Authorization": "Bearer "})

    assert response.status_code == 401


async def test_an_expired_token_is_401(client, session):
    user = UserRepository(session).create(
        first_name="Ana", last_name="P", email="a@example.com", password_hash=hash_password("x1x")
    )
    session.flush()
    expired = jwt.encode(
        {
            "sub": str(user.id),
            "role": user.role.value,
            "type": "access",
            "exp": now_utc() - timedelta(minutes=1),
        },
        settings.jwt_secret,
        algorithm="HS256",
    )

    response = await client.get(PROTECTED, headers=auth(expired))

    assert response.status_code == 401


async def test_a_tampered_token_is_401(client):
    registered = await client.post(REGISTER, json=ACCOUNT)
    token = registered.json()["access_token"]
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")

    response = await client.get(PROTECTED, headers=auth(tampered))

    assert response.status_code == 401


async def test_a_refresh_token_cannot_be_used_as_access(client, session):
    """El refresh vive en una cookie y solo sirve para renovar: aceptarlo acá
    saltearía la rotación de un solo uso."""
    await client.post(REGISTER, json=ACCOUNT)
    user = session.scalars(select(User)).one()

    response = await client.get(PROTECTED, headers=auth(create_refresh_token(user)))

    assert response.status_code == 401


async def test_a_token_of_a_deleted_user_is_401(client, session):
    await client.post(REGISTER, json=ACCOUNT)
    user = session.scalars(select(User)).one()
    token = create_access_token(user)
    session.delete(user)
    session.flush()

    response = await client.get(PROTECTED, headers=auth(token))

    assert response.status_code == 401


async def test_a_suspended_user_is_403_even_with_a_valid_token(client, session):
    """Suspender a alguien lo echa ya, sin esperar los 15 min del access token."""
    registered = await client.post(REGISTER, json=ACCOUNT)
    token = registered.json()["access_token"]
    session.scalars(select(User)).one().status = UserStatus.SUSPENDED
    session.flush()

    response = await client.get(PROTECTED, headers=auth(token))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.parametrize("role", [Role.CUSTOMER, Role.ADMIN, Role.DELIVERY])
async def test_it_works_for_every_role(client, session, role):
    user = UserRepository(session).create(
        first_name="Staff",
        last_name="Morfi",
        email=f"{role.value.lower()}@example.com",
        password_hash=hash_password("secreta123"),
        role=role,
    )
    session.flush()

    response = await client.get(PROTECTED, headers=auth(create_access_token(user)))

    assert response.status_code == 200
    assert response.json()["role"] == role.value
