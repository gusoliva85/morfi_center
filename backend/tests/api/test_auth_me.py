"""Tests de `GET /api/v1/auth/me` (`03_Roadmap.md` T-1.5.3)."""

from __future__ import annotations

import httpx
from sqlalchemy.orm import Session

from app.core.enums import Role, UserStatus
from app.core.security import create_access_token
from app.models.balance import CustomerBalance
from app.models.user import User


async def test_me_returns_own_data_for_a_customer(client: httpx.AsyncClient):
    register = await client.post(
        "/api/v1/auth/register",
        json={
            "first_name": "Gustavo",
            "last_name": "Pérez",
            "email": "gustavo@morficenter.test",
            "phone": "1122334455",
            "password": "cliente123",
        },
    )
    assert register.status_code == 201
    access_token = register.json()["access_token"]

    r = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert r.status_code == 200
    body = r.json()
    assert body == {
        "id": register.json()["user"]["id"],
        "first_name": "Gustavo",
        "last_name": "Pérez",
        "email": "gustavo@morficenter.test",
        "phone": "1122334455",
        "role": "CUSTOMER",
        "balance": 0,
    }


async def test_me_without_token_returns_401(client: httpx.AsyncClient):
    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "NOT_AUTHENTICATED"


def _make_user_with_balance(session: Session, *, role: Role, balance_cents: int) -> User:
    user = User(
        first_name="Ana",
        last_name="Gómez",
        email=f"{role.value.lower()}@morficenter.test",
        password_hash="x",
        role=role,
        status=UserStatus.ACTIVE,
    )
    session.add(user)
    session.flush()
    session.add(CustomerBalance(user_id=user.id, balance=balance_cents))
    session.flush()
    return user


async def test_me_returns_data_for_an_admin(client: httpx.AsyncClient, session: Session):
    admin = _make_user_with_balance(session, role=Role.ADMIN, balance_cents=0)
    token = create_access_token(admin.id, admin.role)
    r = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["role"] == "ADMIN"


async def test_me_returns_data_for_a_delivery(client: httpx.AsyncClient, session: Session):
    delivery = _make_user_with_balance(session, role=Role.DELIVERY, balance_cents=1500)
    token = create_access_token(delivery.id, delivery.role)
    r = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["role"] == "DELIVERY"
    assert body["balance"] == 1500
