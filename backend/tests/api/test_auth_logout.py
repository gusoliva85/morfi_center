"""`POST /api/v1/auth/logout` (`03_Roadmap.md` T-1.4.4)."""

import httpx

from app.core.config import settings

REGISTER = {
    "first_name": "Gustavo",
    "last_name": "Pérez",
    "email": "gustavo@morficenter.test",
    "password": "cliente123",
}


async def test_logout_returns_ok(client: httpx.AsyncClient):
    await client.post("/api/v1/auth/register", json=REGISTER)

    r = await client.post("/api/v1/auth/logout")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


async def test_logout_without_any_session_does_not_error(client: httpx.AsyncClient):
    r = await client.post("/api/v1/auth/logout")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


async def test_logout_clears_the_refresh_cookie(client: httpx.AsyncClient):
    await client.post("/api/v1/auth/register", json=REGISTER)
    assert "mc_refresh" in client.cookies

    r = await client.post("/api/v1/auth/logout")
    cleared_header = next(
        h for h in r.headers.get_list("set-cookie") if h.startswith("mc_refresh=")
    )
    # una cookie borrada se re-envía vacía y con fecha de expiración en el pasado
    assert 'mc_refresh=""' in cleared_header or "mc_refresh=;" in cleared_header
    assert f"Path={settings.api_prefix}/auth" in cleared_header


async def test_refresh_after_logout_returns_401(client: httpx.AsyncClient):
    await client.post("/api/v1/auth/register", json=REGISTER)
    old_refresh = client.cookies.get("mc_refresh")
    assert old_refresh

    logout_resp = await client.post("/api/v1/auth/logout")
    assert logout_resp.status_code == 200

    # el cliente ya no manda la cookie (httpx la borró de su jar); igual
    # probamos explícitamente con el valor que tenía, que ya quedó revocado.
    r = await client.post("/api/v1/auth/refresh", headers={"Cookie": f"mc_refresh={old_refresh}"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "NOT_AUTHENTICATED"


async def test_refresh_with_no_cookie_after_logout_also_401(client: httpx.AsyncClient):
    await client.post("/api/v1/auth/register", json=REGISTER)
    await client.post("/api/v1/auth/logout")

    r = await client.post("/api/v1/auth/refresh")  # httpx ya no tiene la cookie
    assert r.status_code == 401
