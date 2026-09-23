import pytest
from sqlalchemy import select

from app.core.enums import AuthProvider, Role
from app.core.security import decode_token
from app.models import User

ENDPOINT = "/api/v1/auth/register"

VALID = {
    "first_name": "Ana",
    "last_name": "Pérez",
    "email": "ana@example.com",
    "password": "secreta123",
    "phone": "1155551234",
}


async def test_register_returns_201_with_token_and_user(client):
    response = await client.post(ENDPOINT, json=VALID)

    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 900
    assert body["user"]["email"] == "ana@example.com"
    assert body["user"]["role"] == Role.CUSTOMER.value
    assert body["user"]["id"] > 0


async def test_the_access_token_is_usable_and_carries_the_role(client):
    response = await client.post(ENDPOINT, json=VALID)

    payload = decode_token(response.json()["access_token"])
    assert payload["sub"] == str(response.json()["user"]["id"])
    assert payload["role"] == Role.CUSTOMER.value
    assert payload["type"] == "access"


async def test_register_sets_the_refresh_cookie_scoped_to_auth(client):
    response = await client.post(ENDPOINT, json=VALID)

    cookie = response.cookies.get("mc_refresh")
    assert cookie is not None
    assert decode_token(cookie)["type"] == "refresh"

    raw = response.headers["set-cookie"]
    assert "HttpOnly" in raw
    assert "Path=/api/v1/auth" in raw
    assert "SameSite=lax" in raw  # en desarrollo; producción usa none + Secure


async def test_the_response_never_exposes_the_password(client):
    response = await client.post(ENDPOINT, json=VALID)

    assert "password" not in response.text
    assert "password_hash" not in response.text
    assert "secreta123" not in response.text


async def test_register_persists_the_customer_with_cart_and_balance(client, session):
    await client.post(ENDPOINT, json=VALID)

    user = session.scalars(select(User)).one()
    assert user.role == Role.CUSTOMER
    assert user.cart is not None
    assert user.balance.balance == 0
    assert [p.provider for p in user.auth_providers] == [AuthProvider.LOCAL]


async def test_phone_is_optional(client):
    payload = {key: value for key, value in VALID.items() if key != "phone"}

    response = await client.post(ENDPOINT, json=payload)

    assert response.status_code == 201
    assert response.json()["user"]["phone"] is None


async def test_duplicated_email_returns_409_conflict(client):
    await client.post(ENDPOINT, json=VALID)

    response = await client.post(ENDPOINT, json=VALID)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"


async def test_duplicated_email_is_detected_ignoring_case(client):
    await client.post(ENDPOINT, json=VALID)

    response = await client.post(ENDPOINT, json={**VALID, "email": "ANA@Example.com"})

    assert response.status_code == 409


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("email", "no-es-un-email"),
        ("email", ""),
        ("password", "corta1"),
        ("password", "sinnumeros"),
        ("password", "12345678"),
        ("first_name", ""),
        ("first_name", "   "),
        ("last_name", ""),
    ],
)
async def test_invalid_input_returns_422_in_the_project_error_format(client, field, value):
    response = await client.post(ENDPOINT, json={**VALID, field: value})

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert field in [item["field"] for item in error["details"]["fields"]]


async def test_a_missing_field_also_returns_the_project_error_format(client):
    payload = {key: value for key, value in VALID.items() if key != "email"}

    response = await client.post(ENDPOINT, json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert response.json()["error"]["details"]["fields"][0]["field"] == "email"


async def test_invalid_input_does_not_create_any_user(client, session):
    await client.post(ENDPOINT, json={**VALID, "password": "mala"})

    assert session.scalars(select(User)).all() == []


async def test_password_longer_than_bcrypt_limit_is_a_422_not_a_crash(client):
    response = await client.post(ENDPOINT, json={**VALID, "password": "a1" + "x" * 80})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
