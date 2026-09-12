"""`POST /api/v1/auth/register` (`03_Roadmap.md` T-1.3.2)."""

import httpx
import pytest

from app.core.config import settings
from app.core.security import decode_token

VALID = {
    "first_name": "Gustavo",
    "last_name": "Pérez",
    "email": "gustavo@morficenter.test",
    "password": "cliente123",
}


async def test_register_returns_201_with_tokens_and_user(client: httpx.AsyncClient):
    r = await client.post("/api/v1/auth/register", json=VALID)
    assert r.status_code == 201

    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == settings.access_token_minutes * 60
    assert isinstance(body["access_token"], str) and body["access_token"]
    assert body["user"]["email"] == "gustavo@morficenter.test"
    assert body["user"]["role"] == "CUSTOMER"
    assert "password_hash" not in body["user"]
    assert "password" not in body["user"]


async def test_register_sets_httponly_refresh_cookie(client: httpx.AsyncClient):
    r = await client.post("/api/v1/auth/register", json=VALID)
    assert "mc_refresh" in client.cookies

    set_cookie_headers = r.headers.get_list("set-cookie")
    refresh_header = next(h for h in set_cookie_headers if h.startswith("mc_refresh="))
    assert "HttpOnly" in refresh_header
    assert "SameSite=lax" in refresh_header or "samesite=lax" in refresh_header.lower()
    assert f"Path={settings.api_prefix}/auth" in refresh_header


async def test_register_access_token_decodes_with_correct_claims(client: httpx.AsyncClient):
    r = await client.post("/api/v1/auth/register", json=VALID)
    token = r.json()["access_token"]
    payload = decode_token(token, expected_type="access")
    assert payload["role"] == "CUSTOMER"
    assert payload["sub"] == str(r.json()["user"]["id"])


async def test_register_duplicate_email_returns_409_conflict(client: httpx.AsyncClient):
    first = await client.post("/api/v1/auth/register", json=VALID)
    assert first.status_code == 201

    second = await client.post("/api/v1/auth/register", json={**VALID, "first_name": "Otro"})
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "CONFLICT"


@pytest.mark.parametrize(
    "overrides",
    [
        {"email": "no-es-un-email"},
        {"password": "corta1"},
        {"first_name": "123"},
    ],
)
async def test_register_invalid_domain_input_returns_400(client: httpx.AsyncClient, overrides):
    r = await client.post("/api/v1/auth/register", json={**VALID, **overrides})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "INVALID_INPUT"


async def test_register_missing_required_field_returns_422(client: httpx.AsyncClient):
    payload = {k: v for k, v in VALID.items() if k != "email"}
    r = await client.post("/api/v1/auth/register", json=payload)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_register_persists_across_requests_in_the_same_session(client: httpx.AsyncClient):
    # el fixture `client` comparte la `session` del test: registrar y volver a
    # registrar con el mismo email debe verse como duplicado sin commitear.
    await client.post("/api/v1/auth/register", json=VALID)
    r = await client.post("/api/v1/auth/register", json=VALID)
    assert r.status_code == 409
