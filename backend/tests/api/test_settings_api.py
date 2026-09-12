"""Tests de `GET /api/v1/settings` y `PUT /api/v1/settings/{key}` (`03_Roadmap.md` T-2.1.3)."""

from __future__ import annotations

import httpx
from sqlalchemy.orm import Session

from app.core.enums import Role, UserStatus
from app.core.security import create_access_token
from app.db.seed import seed_settings
from app.models.balance import CustomerBalance
from app.models.user import User
from app.services.settings_service import SETTINGS_DEFAULTS


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


async def _register_customer(client: httpx.AsyncClient) -> dict:
    r = await client.post(
        "/api/v1/auth/register",
        json={
            "first_name": "Gustavo",
            "last_name": "Pérez",
            "email": "gustavo@morficenter.test",
            "password": "cliente123",
        },
    )
    assert r.status_code == 201
    return r.json()["user"]


# ── GET /settings ─────────────────────────────────────────
async def test_admin_sees_every_known_key_with_its_default(
    client: httpx.AsyncClient, session: Session
):
    headers = _admin_headers(session)
    r = await client.get("/api/v1/settings", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["timezone"] == "America/Argentina/Buenos_Aires"
    assert body["orders.code_prefix"] == "MC"
    assert "payment.transfer" in body


async def test_after_seed_settings_get_returns_the_full_set(
    client: httpx.AsyncClient, session: Session
):
    headers = _admin_headers(session)
    seed_settings(session)

    r = await client.get("/api/v1/settings", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == {key.value for key in SETTINGS_DEFAULTS}


async def test_customer_cannot_list_settings(client: httpx.AsyncClient):
    customer = await _register_customer(client)
    token = create_access_token(customer["id"], "CUSTOMER")
    r = await client.get("/api/v1/settings", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


# ── PUT /settings/{key} ────────────────────────────────────
async def test_admin_updates_payment_transfer(client: httpx.AsyncClient, session: Session):
    headers = _admin_headers(session)
    payload = {"alias": "NUEVO.ALIAS", "holder": "Morfi SRL", "bank": "Banco Z", "cbu": "999"}

    r = await client.put(
        "/api/v1/settings/payment.transfer", json={"value": payload}, headers=headers
    )
    assert r.status_code == 200
    assert r.json() == {"key": "payment.transfer", "value": payload}

    listing = await client.get("/api/v1/settings", headers=headers)
    assert listing.json()["payment.transfer"] == payload


async def test_customer_cannot_update_settings(client: httpx.AsyncClient):
    customer = await _register_customer(client)
    token = create_access_token(customer["id"], "CUSTOMER")
    r = await client.put(
        "/api/v1/settings/payment.transfer",
        json={"value": {"alias": "x", "holder": "x", "bank": "x", "cbu": "x"}},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


async def test_update_unknown_key_returns_404(client: httpx.AsyncClient, session: Session):
    headers = _admin_headers(session)
    r = await client.put("/api/v1/settings/no.existe", json={"value": "x"}, headers=headers)
    assert r.status_code == 404


async def test_update_with_invalid_shape_returns_400(client: httpx.AsyncClient, session: Session):
    headers = _admin_headers(session)
    r = await client.put(
        "/api/v1/settings/coverage.mode", json={"value": "not-a-real-mode"}, headers=headers
    )
    assert r.status_code == 400
    assert r.json()["error"]["details"]["field"] == "coverage.mode"


async def test_without_token_returns_401(client: httpx.AsyncClient):
    r = await client.get("/api/v1/settings")
    assert r.status_code == 401
