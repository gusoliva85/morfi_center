"""`POST /api/v1/auth/refresh` (`03_Roadmap.md` T-1.4.3)."""

import httpx

from app.core.config import settings
from app.core.security import decode_token

REGISTER = {
    "first_name": "Gustavo",
    "last_name": "Pérez",
    "email": "gustavo@morficenter.test",
    "password": "cliente123",
}


async def test_refresh_with_valid_cookie_returns_new_access_token(client: httpx.AsyncClient):
    reg = await client.post("/api/v1/auth/register", json=REGISTER)
    user_id = reg.json()["user"]["id"]
    assert "mc_refresh" in client.cookies  # el jar de httpx la guardó sola

    r = await client.post("/api/v1/auth/refresh")
    assert r.status_code == 200

    body = r.json()
    assert body["user"]["email"] == REGISTER["email"]
    assert body["expires_in"] == settings.access_token_minutes * 60
    payload = decode_token(body["access_token"], expected_type="access")
    assert payload["role"] == "CUSTOMER"
    assert payload["sub"] == str(user_id)


async def test_refresh_sets_a_new_rotated_cookie(client: httpx.AsyncClient):
    await client.post("/api/v1/auth/register", json=REGISTER)
    old_refresh = client.cookies.get("mc_refresh")

    r = await client.post("/api/v1/auth/refresh")
    new_refresh = client.cookies.get("mc_refresh")

    assert new_refresh is not None
    assert new_refresh != old_refresh
    refresh_header = next(
        h for h in r.headers.get_list("set-cookie") if h.startswith("mc_refresh=")
    )
    assert "HttpOnly" in refresh_header
    assert f"Path={settings.api_prefix}/auth" in refresh_header


async def test_refresh_without_cookie_returns_401(client: httpx.AsyncClient):
    r = await client.post("/api/v1/auth/refresh")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "NOT_AUTHENTICATED"


async def test_refresh_reused_token_after_rotation_returns_401(client: httpx.AsyncClient):
    await client.post("/api/v1/auth/register", json=REGISTER)
    old_refresh = client.cookies.get("mc_refresh")
    assert old_refresh

    r1 = await client.post("/api/v1/auth/refresh")  # rota: revoca `old_refresh`
    assert r1.status_code == 200
    assert client.cookies.get("mc_refresh") != old_refresh

    # reintento con la cookie vieja, ya rotada -> 401 (no distingue el motivo)
    r2 = await client.post("/api/v1/auth/refresh", headers={"Cookie": f"mc_refresh={old_refresh}"})
    assert r2.status_code == 401
    assert r2.json()["error"]["code"] == "NOT_AUTHENTICATED"


async def test_refresh_with_garbage_cookie_returns_401(client: httpx.AsyncClient):
    r = await client.post(
        "/api/v1/auth/refresh", headers={"Cookie": "mc_refresh=esto-no-es-un-jwt"}
    )
    assert r.status_code == 401


async def test_refresh_can_be_called_repeatedly_when_using_the_rotated_cookie(
    client: httpx.AsyncClient,
):
    # uso normal: cada refresh sucesivo usa la cookie que dejó el anterior,
    # y cada rotación entrega un refresh (jti) distinto del anterior.
    await client.post("/api/v1/auth/register", json=REGISTER)
    r0_refresh = client.cookies.get("mc_refresh")

    r1 = await client.post("/api/v1/auth/refresh")
    assert r1.status_code == 200
    r1_refresh = client.cookies.get("mc_refresh")
    assert r1_refresh != r0_refresh

    r2 = await client.post("/api/v1/auth/refresh")
    assert r2.status_code == 200
    r2_refresh = client.cookies.get("mc_refresh")
    assert r2_refresh != r1_refresh
