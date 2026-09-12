"""Tests de `app/api/deps.py::require_role` (`03_Roadmap.md` T-1.5.2).

Igual que en `test_deps.py`, todavía no hay un endpoint real que exija un rol
puntual (llega recién en fases posteriores), así que se montan endpoints
mínimos ad-hoc solo para probar la dependencia contra la app completa.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest_asyncio
from fastapi import APIRouter, Depends
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.core.enums import Role, UserStatus
from app.core.security import create_access_token
from app.db.session import get_session
from app.main import create_app
from app.models.user import User

_role_router = APIRouter()


@_role_router.get("/_test/admin-only")
def _admin_only_endpoint(user: User = Depends(require_role(Role.ADMIN))) -> dict:
    return {"id": user.id, "role": user.role.value}


@_role_router.get("/_test/admin-or-delivery")
def _admin_or_delivery_endpoint(
    user: User = Depends(require_role(Role.ADMIN, Role.DELIVERY)),
) -> dict:
    return {"id": user.id, "role": user.role.value}


@pytest_asyncio.fixture
async def role_client(engine: Engine, session: Session) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app()
    app.include_router(_role_router, prefix="/api/v1")
    app.dependency_overrides[get_session] = lambda: session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.clear()


def _make_user(session: Session, *, role: Role) -> User:
    user = User(
        first_name="Gustavo",
        last_name="Pérez",
        email=f"{role.value.lower()}@morficenter.test",
        password_hash="x",
        role=role,
        status=UserStatus.ACTIVE,
    )
    session.add(user)
    session.flush()
    return user


async def test_admin_can_access_admin_only_endpoint(role_client, session: Session):
    admin = _make_user(session, role=Role.ADMIN)
    token = create_access_token(admin.id, admin.role)
    r = await role_client.get(
        "/api/v1/_test/admin-only", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200
    assert r.json() == {"id": admin.id, "role": "ADMIN"}


async def test_customer_gets_403_on_admin_only_endpoint(role_client, session: Session):
    customer = _make_user(session, role=Role.CUSTOMER)
    token = create_access_token(customer.id, customer.role)
    r = await role_client.get(
        "/api/v1/_test/admin-only", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "FORBIDDEN"


async def test_no_token_returns_401_before_checking_role(role_client):
    # sin sesión, el error correcto es 401 (no autenticado), no 403.
    r = await role_client.get("/api/v1/_test/admin-only")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "NOT_AUTHENTICATED"


async def test_multiple_allowed_roles(role_client, session: Session):
    delivery = _make_user(session, role=Role.DELIVERY)
    token = create_access_token(delivery.id, delivery.role)
    r = await role_client.get(
        "/api/v1/_test/admin-or-delivery", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200

    customer = _make_user(session, role=Role.CUSTOMER)
    token = create_access_token(customer.id, customer.role)
    r = await role_client.get(
        "/api/v1/_test/admin-or-delivery", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 403
