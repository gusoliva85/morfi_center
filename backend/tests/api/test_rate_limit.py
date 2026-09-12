"""Rate limiting en `/auth/register` y `/auth/login` (`03_Roadmap.md` T-1.4.5)."""

import httpx

from app.core.rate_limit import DEFAULT_AUTH_LIMIT

assert DEFAULT_AUTH_LIMIT == "10/minute"  # si esto cambia, ajustar los rangos de abajo


async def test_11th_register_in_a_minute_returns_429(client: httpx.AsyncClient):
    for n in range(10):
        r = await client.post(
            "/api/v1/auth/register",
            json={
                "first_name": "Gustavo",
                "last_name": "Pérez",
                "email": f"user{n}@morficenter.test",
                "password": "cliente123",
            },
        )
        assert r.status_code == 201, f"intento {n + 1} debería pasar el límite"

    r11 = await client.post(
        "/api/v1/auth/register",
        json={
            "first_name": "Gustavo",
            "last_name": "Pérez",
            "email": "user10@morficenter.test",
            "password": "cliente123",
        },
    )
    assert r11.status_code == 429
    assert r11.json()["error"]["code"] == "TOO_MANY_REQUESTS"


async def test_11th_login_attempt_in_a_minute_returns_429(client: httpx.AsyncClient):
    # los intentos cuentan aunque las credenciales sean incorrectas: el límite
    # frena fuerza bruta, así que se evalúa ANTES de validar el password.
    for n in range(10):
        r = await client.post(
            "/api/v1/auth/login",
            json={"email": "nadie@morficenter.test", "password": f"intento{n}"},
        )
        assert r.status_code == 401, f"intento {n + 1} debería pasar el límite"

    r11 = await client.post(
        "/api/v1/auth/login",
        json={"email": "nadie@morficenter.test", "password": "intento10"},
    )
    assert r11.status_code == 429
    assert r11.json()["error"]["code"] == "TOO_MANY_REQUESTS"


async def test_register_and_login_limits_are_independent_per_endpoint(client: httpx.AsyncClient):
    # gastar el cupo de /register no debe afectar a /login.
    for n in range(10):
        await client.post(
            "/api/v1/auth/register",
            json={
                "first_name": "Gustavo",
                "last_name": "Pérez",
                "email": f"otro{n}@morficenter.test",
                "password": "cliente123",
            },
        )
    blocked = await client.post(
        "/api/v1/auth/register",
        json={
            "first_name": "Gustavo",
            "last_name": "Pérez",
            "email": "otro10@morficenter.test",
            "password": "cliente123",
        },
    )
    assert blocked.status_code == 429

    login_still_ok = await client.post(
        "/api/v1/auth/login", json={"email": "nadie@morficenter.test", "password": "x"}
    )
    assert login_still_ok.status_code == 401  # no 429: /login tiene su propio cupo


async def test_health_endpoint_is_not_rate_limited(client: httpx.AsyncClient):
    for _ in range(15):
        r = await client.get("/api/v1/health")
        assert r.status_code == 200
