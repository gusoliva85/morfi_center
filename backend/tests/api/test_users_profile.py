"""Tests de `PATCH /api/v1/users/me/profile` (`03_Roadmap.md` T-1.6.1)."""

from __future__ import annotations

import httpx


async def _register(client: httpx.AsyncClient) -> str:
    r = await client.post(
        "/api/v1/auth/register",
        json={
            "first_name": "Gustavo",
            "last_name": "Pérez",
            "email": "gustavo@morficenter.test",
            "phone": "1122334455",
            "password": "cliente123",
        },
    )
    assert r.status_code == 201
    return r.json()["access_token"]


async def test_update_phone_persists(client: httpx.AsyncClient):
    token = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.patch(
        "/api/v1/users/me/profile", json={"phone": "1155556666"}, headers=headers
    )
    assert r.status_code == 200
    assert r.json()["phone"] == "1155556666"

    me = await client.get("/api/v1/auth/me", headers=headers)
    assert me.json()["phone"] == "1155556666"


async def test_update_first_and_last_name(client: httpx.AsyncClient):
    token = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.patch(
        "/api/v1/users/me/profile",
        json={"first_name": "Mariana", "last_name": "López"},
        headers=headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["first_name"] == "Mariana"
    assert body["last_name"] == "López"


async def test_partial_update_leaves_other_fields_unchanged(client: httpx.AsyncClient):
    token = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.patch("/api/v1/users/me/profile", json={"last_name": "Gómez"}, headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["first_name"] == "Gustavo"  # no enviado, no cambia
    assert body["phone"] == "1122334455"  # no enviado, no cambia


async def test_email_is_not_editable_via_this_endpoint(client: httpx.AsyncClient):
    token = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.patch(
        "/api/v1/users/me/profile",
        json={"email": "otro@morficenter.test", "last_name": "Gómez"},
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["email"] == "gustavo@morficenter.test"  # sin cambios


async def test_invalid_phone_returns_400(client: httpx.AsyncClient):
    token = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.patch("/api/v1/users/me/profile", json={"phone": "abc"}, headers=headers)
    assert r.status_code == 400
    assert r.json()["error"]["details"]["field"] == "phone"


async def test_without_token_returns_401(client: httpx.AsyncClient):
    r = await client.patch("/api/v1/users/me/profile", json={"phone": "1155556666"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "NOT_AUTHENTICATED"
