import pytest
from sqlalchemy import func, select

from app.core.rate_limit import AUTH_RATE_LIMIT
from app.models import User

LOGIN = "/api/v1/auth/login"
REGISTER = "/api/v1/auth/register"
REFRESH = "/api/v1/auth/refresh"

LIMIT = int(AUTH_RATE_LIMIT.split("/")[0])

EMAIL = "ana@example.com"
PASSWORD = "secreta123"
ACCOUNT = {"first_name": "Ana", "last_name": "Pérez", "email": EMAIL, "password": PASSWORD}


async def test_the_limit_allows_the_first_attempts(client):
    """Un usuario que se equivoca varias veces seguidas no debe quedar bloqueado
    antes de llegar al límite."""
    await client.post(REGISTER, json=ACCOUNT)

    for _ in range(LIMIT):
        response = await client.post(LOGIN, json={"email": EMAIL, "password": "mala-1234"})
        assert response.status_code == 401


async def test_too_many_login_attempts_return_429(client):
    await client.post(REGISTER, json=ACCOUNT)

    for _ in range(LIMIT):
        await client.post(LOGIN, json={"email": EMAIL, "password": "mala-1234"})

    response = await client.post(LOGIN, json={"email": EMAIL, "password": "mala-1234"})

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "TOO_MANY_REQUESTS"


async def test_the_429_includes_retry_after(client):
    for _ in range(LIMIT + 1):
        response = await client.post(LOGIN, json={"email": EMAIL, "password": "mala-1234"})

    assert response.status_code == 429
    assert response.headers["retry-after"] == "60"


async def test_the_limit_blocks_even_with_the_right_password(client):
    """Si no, alguien que adivina la contraseña al intento 15 seguiría entrando."""
    await client.post(REGISTER, json=ACCOUNT)
    for _ in range(LIMIT):
        await client.post(LOGIN, json={"email": EMAIL, "password": "mala-1234"})

    response = await client.post(LOGIN, json={"email": EMAIL, "password": PASSWORD})

    assert response.status_code == 429


async def test_register_has_its_own_limit(client):
    for i in range(LIMIT):
        await client.post(REGISTER, json={**ACCOUNT, "email": f"u{i}@example.com"})

    response = await client.post(REGISTER, json={**ACCOUNT, "email": "otro@example.com"})

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "TOO_MANY_REQUESTS"


async def test_a_blocked_register_does_not_create_the_user(client, session):
    for i in range(LIMIT):
        await client.post(REGISTER, json={**ACCOUNT, "email": f"u{i}@example.com"})

    await client.post(REGISTER, json={**ACCOUNT, "email": "bloqueado@example.com"})

    assert session.scalar(select(func.count()).select_from(User)) == LIMIT


async def test_login_and_register_have_separate_buckets(client):
    """Agotar el límite de login no debe impedir registrarse (y al revés)."""
    for _ in range(LIMIT + 1):
        await client.post(LOGIN, json={"email": EMAIL, "password": "mala-1234"})

    response = await client.post(REGISTER, json=ACCOUNT)

    assert response.status_code == 201


async def test_refresh_is_not_rate_limited(client):
    """El front lo llama seguido de forma legítima (cada vez que vence el access):
    limitarlo desconectaría a usuarios normales."""
    await client.post(REGISTER, json=ACCOUNT)

    for _ in range(LIMIT + 5):
        response = await client.post(REFRESH)
        assert response.status_code == 200


@pytest.mark.parametrize("endpoint", [LOGIN, REGISTER])
async def test_the_429_uses_the_project_error_format(client, endpoint):
    for _ in range(LIMIT + 1):
        response = await client.post(endpoint, json=ACCOUNT)

    body = response.json()
    assert response.status_code == 429
    assert set(body["error"]) == {"code", "message", "details"}
    assert body["error"]["message"]
