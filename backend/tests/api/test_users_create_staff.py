"""Tests de `POST /api/v1/users` (`03_Roadmap.md` T-1.7.1)."""

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


async def test_admin_creates_a_delivery_with_generated_password(
    client: httpx.AsyncClient, session: Session
):
    headers = _admin_headers(session)
    r = await client.post(
        "/api/v1/users",
        json={
            "first_name": "Carlos",
            "last_name": "Ruiz",
            "email": "carlos@morficenter.test",
            "role": "DELIVERY",
            "vehicle_type": "moto",
            "capacity": 3,
        },
        headers=headers,
    )
    assert r.status_code == 201
    body = r.json()
    assert body["role"] == "DELIVERY"
    assert body["email"] == "carlos@morficenter.test"
    assert body["temporary_password"] is not None
    assert len(body["temporary_password"]) >= 8


async def test_admin_creates_an_admin_with_explicit_password(
    client: httpx.AsyncClient, session: Session
):
    headers = _admin_headers(session)
    r = await client.post(
        "/api/v1/users",
        json={
            "first_name": "Laura",
            "last_name": "Díaz",
            "email": "laura@morficenter.test",
            "role": "ADMIN",
            "password": "admin1234",
        },
        headers=headers,
    )
    assert r.status_code == 201
    body = r.json()
    assert body["role"] == "ADMIN"
    assert body["temporary_password"] is None

    login = await client.post(
        "/api/v1/auth/login", json={"email": "laura@morficenter.test", "password": "admin1234"}
    )
    assert login.status_code == 200


async def test_customer_cannot_create_staff(client: httpx.AsyncClient):
    register = await client.post(
        "/api/v1/auth/register",
        json={
            "first_name": "Gustavo",
            "last_name": "Pérez",
            "email": "gustavo@morficenter.test",
            "password": "cliente123",
        },
    )
    token = register.json()["access_token"]

    r = await client.post(
        "/api/v1/users",
        json={
            "first_name": "Carlos",
            "last_name": "Ruiz",
            "email": "carlos@morficenter.test",
            "role": "DELIVERY",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "FORBIDDEN"


async def test_without_token_returns_401(client: httpx.AsyncClient):
    r = await client.post(
        "/api/v1/users",
        json={
            "first_name": "Carlos",
            "last_name": "Ruiz",
            "email": "carlos@morficenter.test",
            "role": "DELIVERY",
        },
    )
    assert r.status_code == 401


async def test_customer_role_is_rejected(client: httpx.AsyncClient, session: Session):
    headers = _admin_headers(session)
    r = await client.post(
        "/api/v1/users",
        json={
            "first_name": "Carlos",
            "last_name": "Ruiz",
            "email": "carlos@morficenter.test",
            "role": "CUSTOMER",
        },
        headers=headers,
    )
    assert r.status_code == 400
    assert r.json()["error"]["details"]["field"] == "role"


async def test_duplicate_email_returns_409(client: httpx.AsyncClient, session: Session):
    headers = _admin_headers(session)
    payload = {
        "first_name": "Carlos",
        "last_name": "Ruiz",
        "email": "carlos@morficenter.test",
        "role": "DELIVERY",
    }
    first = await client.post("/api/v1/users", json=payload, headers=headers)
    assert first.status_code == 201

    second = await client.post("/api/v1/users", json=payload, headers=headers)
    assert second.status_code == 409
