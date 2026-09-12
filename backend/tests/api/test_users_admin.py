"""Tests de `GET /api/v1/users` y `PATCH /api/v1/users/{id}` (`03_Roadmap.md` T-1.7.2)."""

from __future__ import annotations

import httpx
from sqlalchemy.orm import Session

from app.core.enums import Role, UserStatus
from app.core.security import create_access_token
from app.models.balance import CustomerBalance
from app.models.user import User


def _make_admin(session: Session) -> User:
    admin = User(
        first_name="Root",
        last_name="Admin",
        email="admin@morficenter.test",
        password_hash="x",
        role=Role.ADMIN,
        status=UserStatus.ACTIVE,
    )
    session.add(admin)
    session.flush()
    session.add(CustomerBalance(user_id=admin.id, balance=0))
    session.flush()
    return admin


def _admin_headers(session: Session) -> dict[str, str]:
    admin = _make_admin(session)
    token = create_access_token(admin.id, admin.role)
    return {"Authorization": f"Bearer {token}"}


async def _register_customer(client: httpx.AsyncClient, n: int = 0) -> dict:
    r = await client.post(
        "/api/v1/auth/register",
        json={
            "first_name": "Gustavo",
            "last_name": "Pérez",
            "email": f"cliente{n}@morficenter.test",
            "password": "cliente123",
        },
    )
    assert r.status_code == 201
    return r.json()["user"]


# ── GET /users ────────────────────────────────────────────
async def test_list_users_returns_everyone_paginated(client: httpx.AsyncClient, session: Session):
    headers = _admin_headers(session)
    await _register_customer(client, 1)
    await _register_customer(client, 2)

    r = await client.get("/api/v1/users", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 3  # 2 clientes + el admin de este test
    assert body["page"] == 1
    assert len(body["items"]) == 3


async def test_list_users_filters_by_role(client: httpx.AsyncClient, session: Session):
    headers = _admin_headers(session)
    await _register_customer(client, 1)
    await _register_customer(client, 2)

    r = await client.get("/api/v1/users", params={"role": "CUSTOMER"}, headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2
    assert all(u["role"] == "CUSTOMER" for u in body["items"])


async def test_list_users_customer_gets_403(client: httpx.AsyncClient):
    customer = await _register_customer(client)
    token = create_access_token(customer["id"], "CUSTOMER")
    r = await client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


# ── PATCH /users/{id} ─────────────────────────────────────
async def test_admin_suspends_a_user_and_it_cannot_login(
    client: httpx.AsyncClient, session: Session
):
    headers = _admin_headers(session)
    customer = await _register_customer(client)

    r = await client.patch(
        f"/api/v1/users/{customer['id']}", json={"status": "SUSPENDED"}, headers=headers
    )
    assert r.status_code == 200
    assert r.json()["status"] == "SUSPENDED"

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "cliente0@morficenter.test", "password": "cliente123"},
    )
    assert login.status_code == 403


async def test_admin_changes_role(client: httpx.AsyncClient, session: Session):
    headers = _admin_headers(session)
    customer = await _register_customer(client)

    r = await client.patch(
        f"/api/v1/users/{customer['id']}", json={"role": "DELIVERY"}, headers=headers
    )
    assert r.status_code == 200
    assert r.json()["role"] == "DELIVERY"


async def test_customer_cannot_edit_users(client: httpx.AsyncClient):
    customer = await _register_customer(client, 1)
    other = await _register_customer(client, 2)
    token = create_access_token(customer["id"], "CUSTOMER")

    r = await client.patch(
        f"/api/v1/users/{other['id']}",
        json={"status": "SUSPENDED"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


async def test_patch_nonexistent_user_returns_404(client: httpx.AsyncClient, session: Session):
    headers = _admin_headers(session)
    r = await client.patch("/api/v1/users/999999", json={"status": "SUSPENDED"}, headers=headers)
    assert r.status_code == 404


async def test_patch_without_role_or_status_returns_400(
    client: httpx.AsyncClient, session: Session
):
    headers = _admin_headers(session)
    customer = await _register_customer(client)
    r = await client.patch(f"/api/v1/users/{customer['id']}", json={}, headers=headers)
    assert r.status_code == 400
