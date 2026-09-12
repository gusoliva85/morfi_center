"""`POST /api/v1/auth/login` (`03_Roadmap.md` T-1.4.2)."""

import httpx
import pytest
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.enums import UserStatus
from app.core.security import decode_token
from app.repositories.user_repository import UserRepository

REGISTER = {
    "first_name": "Gustavo",
    "last_name": "Pérez",
    "email": "gustavo@morficenter.test",
    "password": "cliente123",
}


async def _register(client: httpx.AsyncClient) -> None:
    r = await client.post("/api/v1/auth/register", json=REGISTER)
    assert r.status_code == 201
    client.cookies.clear()  # login parte de cero, sin la cookie del registro


async def test_login_returns_200_with_tokens_and_user(client: httpx.AsyncClient):
    await _register(client)

    r = await client.post(
        "/api/v1/auth/login", json={"email": REGISTER["email"], "password": REGISTER["password"]}
    )
    assert r.status_code == 200

    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == settings.access_token_minutes * 60
    assert body["user"]["email"] == REGISTER["email"]
    assert "password_hash" not in body["user"]


async def test_login_sets_httponly_refresh_cookie(client: httpx.AsyncClient):
    await _register(client)

    r = await client.post(
        "/api/v1/auth/login", json={"email": REGISTER["email"], "password": REGISTER["password"]}
    )
    assert "mc_refresh" in client.cookies
    refresh_header = next(
        h for h in r.headers.get_list("set-cookie") if h.startswith("mc_refresh=")
    )
    assert "HttpOnly" in refresh_header
    assert f"Path={settings.api_prefix}/auth" in refresh_header


async def test_login_access_token_decodes_with_correct_claims(client: httpx.AsyncClient):
    await _register(client)

    r = await client.post(
        "/api/v1/auth/login", json={"email": REGISTER["email"], "password": REGISTER["password"]}
    )
    payload = decode_token(r.json()["access_token"], expected_type="access")
    assert payload["role"] == "CUSTOMER"
    assert payload["sub"] == str(r.json()["user"]["id"])


async def test_login_is_case_and_space_insensitive_on_email(client: httpx.AsyncClient):
    await _register(client)

    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "  GUSTAVO@MorfiCenter.TEST  ", "password": REGISTER["password"]},
    )
    assert r.status_code == 200


async def test_login_wrong_password_returns_401_generic(client: httpx.AsyncClient):
    await _register(client)

    r = await client.post(
        "/api/v1/auth/login", json={"email": REGISTER["email"], "password": "contraseña-mala1"}
    )
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "NOT_AUTHENTICATED"


async def test_login_unknown_email_returns_the_same_401_message(client: httpx.AsyncClient):
    await _register(client)

    r_unknown = await client.post(
        "/api/v1/auth/login",
        json={"email": "no-existe@morficenter.test", "password": "cualquiera1"},
    )
    r_wrong_pw = await client.post(
        "/api/v1/auth/login", json={"email": REGISTER["email"], "password": "otra-mala1"}
    )
    assert r_unknown.status_code == r_wrong_pw.status_code == 401
    assert r_unknown.json()["error"]["message"] == r_wrong_pw.json()["error"]["message"]


async def test_login_suspended_account_returns_403(client: httpx.AsyncClient, session: Session):
    await _register(client)
    repo = UserRepository(session)
    user = repo.get_by_email(REGISTER["email"])
    user.status = UserStatus.SUSPENDED
    session.flush()

    r = await client.post(
        "/api/v1/auth/login", json={"email": REGISTER["email"], "password": REGISTER["password"]}
    )
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.parametrize(
    "payload", [{"email": "gustavo@morficenter.test"}, {"password": "algo123"}, {}]
)
async def test_login_missing_field_returns_422(client: httpx.AsyncClient, payload):
    r = await client.post("/api/v1/auth/login", json=payload)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"
