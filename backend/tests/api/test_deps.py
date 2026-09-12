"""Tests de `app/api/deps.py::get_current_user` (`03_Roadmap.md` T-1.5.1).

Todavía no existe un endpoint real protegido (llega en T-1.5.3, `/auth/me`),
así que se monta uno mínimo ad-hoc solo para poder probar la dependencia
contra la app completa (incluidos los handlers de error).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import timedelta

import httpx
import pytest_asyncio
from fastapi import APIRouter, Depends
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.enums import Role, UserStatus
from app.core.security import create_access_token, create_refresh_token
from app.core.timezone import now_utc
from app.db.session import get_session
from app.main import create_app
from app.models.user import User

_protected_router = APIRouter()


@_protected_router.get("/_test/protected")
def _protected_endpoint(user: User = Depends(get_current_user)) -> dict:
    return {"id": user.id, "email": user.email, "role": user.role.value}


@pytest_asyncio.fixture
async def protected_client(engine: Engine, session: Session) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app()
    app.include_router(_protected_router, prefix="/api/v1")
    app.dependency_overrides[get_session] = lambda: session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.clear()


def _make_user(session: Session, *, status: UserStatus = UserStatus.ACTIVE) -> User:
    user = User(
        first_name="Gustavo",
        last_name="Pérez",
        email="gustavo@morficenter.test",
        password_hash="x",
        role=Role.CUSTOMER,
        status=status,
    )
    session.add(user)
    session.flush()
    return user


async def test_valid_token_returns_200_with_user_data(protected_client, session: Session):
    user = _make_user(session)
    token = create_access_token(user.id, user.role)
    r = await protected_client.get(
        "/api/v1/_test/protected", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200
    assert r.json() == {"id": user.id, "email": user.email, "role": "CUSTOMER"}


async def test_missing_token_returns_401(protected_client):
    r = await protected_client.get("/api/v1/_test/protected")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "NOT_AUTHENTICATED"


async def test_expired_token_returns_401(protected_client, session: Session):
    user = _make_user(session)
    expired_token = create_access_token(user.id, user.role, now=now_utc() - timedelta(minutes=20))
    r = await protected_client.get(
        "/api/v1/_test/protected", headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "NOT_AUTHENTICATED"


async def test_malformed_token_returns_401(protected_client):
    r = await protected_client.get(
        "/api/v1/_test/protected", headers={"Authorization": "Bearer no-soy-un-jwt"}
    )
    assert r.status_code == 401


async def test_refresh_token_is_rejected(protected_client, session: Session):
    # la dependencia exige type=access; un refresh token no debe servir acá.
    user = _make_user(session)
    refresh_token, _jti = create_refresh_token(user.id)
    r = await protected_client.get(
        "/api/v1/_test/protected", headers={"Authorization": f"Bearer {refresh_token}"}
    )
    assert r.status_code == 401


async def test_suspended_user_returns_401(protected_client, session: Session):
    user = _make_user(session, status=UserStatus.SUSPENDED)
    token = create_access_token(user.id, user.role)
    r = await protected_client.get(
        "/api/v1/_test/protected", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 401


async def test_nonexistent_user_returns_401(protected_client):
    token = create_access_token(999_999, Role.CUSTOMER)
    r = await protected_client.get(
        "/api/v1/_test/protected", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 401
