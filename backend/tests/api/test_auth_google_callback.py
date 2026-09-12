"""Tests de `GET /api/v1/auth/google/callback` (`03_Roadmap.md` T-1.8.2).

`exchange_code_for_tokens` y `verify_google_id_token` se mockean siempre acá
(nunca se llega a golpear la red real de Google) — el `state`/PKCE sí se
ejercitan de punta a punta pasando primero por `/auth/google/login` real.
"""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.enums import Role, UserStatus
from app.core.security import create_access_token
from app.models.balance import CustomerBalance
from app.models.user import User, UserAuthProvider
from app.services.external.google_oauth import InvalidGoogleTokenError

GOOGLE_CLAIMS = {
    "sub": "1234567890",
    "email": "gustavo@morficenter.test",
    "given_name": "Gustavo",
    "family_name": "Pérez",
}


@pytest.fixture(autouse=True)
def _google_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "google_client_id", "test-client-id.apps.googleusercontent.com")
    monkeypatch.setattr(settings, "google_client_secret", "test-client-secret")
    monkeypatch.setattr(
        settings, "google_redirect_uri", "http://localhost:8000/api/v1/auth/google/callback"
    )


async def _start_flow(client: httpx.AsyncClient) -> str:
    """Pega a `/google/login` (cookie `mc_oauth_state` real) y devuelve el
    `state` que le corresponde, para poder llamar al callback como si Google
    hubiera redirigido de vuelta con ese mismo valor."""
    r = await client.get("/api/v1/auth/google/login")
    assert r.status_code == 302
    return parse_qs(urlparse(r.headers["location"]).query)["state"][0]


def _mock_google(monkeypatch: pytest.MonkeyPatch, claims: dict | None = None) -> None:
    monkeypatch.setattr(
        "app.api.routes.auth.exchange_code_for_tokens",
        lambda code, code_verifier: {"id_token": "fake-id-token", "access_token": "fake-at"},
    )
    monkeypatch.setattr(
        "app.api.routes.auth.verify_google_id_token",
        lambda id_token: claims or GOOGLE_CLAIMS,
    )


# ── camino 1: usuario nuevo ───────────────────────────────
async def test_new_user_is_created_and_logged_in(
    client: httpx.AsyncClient, session, monkeypatch: pytest.MonkeyPatch
):
    _mock_google(monkeypatch)
    state = await _start_flow(client)

    r = await client.get("/api/v1/auth/google/callback", params={"code": "abc123", "state": state})

    assert r.status_code == 302
    location = r.headers["location"]
    assert location.startswith(f"{settings.frontend_origin}/pages/auth/login.html#access_token=")
    assert "mc_refresh" in r.cookies

    user = session.scalars(select(User).where(User.email == GOOGLE_CLAIMS["email"])).one()
    assert user.password_hash is None
    assert user.first_name == "Gustavo"


async def test_oauth_state_cookie_is_cleared_after_the_callback(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    _mock_google(monkeypatch)
    state = await _start_flow(client)

    r = await client.get("/api/v1/auth/google/callback", params={"code": "abc123", "state": state})
    assert r.cookies.get("mc_oauth_state") is None


# ── camino 2: vincula a una cuenta local existente ────────
async def test_links_google_to_an_existing_local_account(
    client: httpx.AsyncClient, session, monkeypatch: pytest.MonkeyPatch
):
    register = await client.post(
        "/api/v1/auth/register",
        json={
            "first_name": "Gustavo",
            "last_name": "Pérez",
            "email": "gustavo@morficenter.test",
            "password": "cliente123",
        },
    )
    local_user_id = register.json()["user"]["id"]

    _mock_google(monkeypatch)
    state = await _start_flow(client)
    r = await client.get("/api/v1/auth/google/callback", params={"code": "abc123", "state": state})
    assert r.status_code == 302

    providers = session.scalars(
        select(UserAuthProvider).where(UserAuthProvider.user_id == local_user_id)
    ).all()
    assert {p.provider.value for p in providers} == {"local", "google"}


# ── camino 3: login (provider ya vinculado) ───────────────
async def test_second_login_with_the_same_google_account_reuses_the_user(
    client: httpx.AsyncClient, session, monkeypatch: pytest.MonkeyPatch
):
    _mock_google(monkeypatch)

    state_1 = await _start_flow(client)
    first = await client.get(
        "/api/v1/auth/google/callback", params={"code": "abc123", "state": state_1}
    )
    first_user = session.scalars(select(User).where(User.email == GOOGLE_CLAIMS["email"])).one()

    state_2 = await _start_flow(client)
    second = await client.get(
        "/api/v1/auth/google/callback", params={"code": "xyz789", "state": state_2}
    )

    assert first.status_code == 302
    assert second.status_code == 302
    providers = session.scalars(
        select(UserAuthProvider).where(UserAuthProvider.user_id == first_user.id)
    ).all()
    assert len(providers) == 1  # no duplica el provider en el segundo login


# ── errores: siempre redirige, nunca JSON crudo ───────────
async def test_missing_code_redirects_with_error(client: httpx.AsyncClient):
    r = await client.get("/api/v1/auth/google/callback", params={"state": "whatever"})
    assert r.status_code == 302
    assert "error=google_auth_failed" in r.headers["location"]


async def test_missing_state_cookie_redirects_with_error(client: httpx.AsyncClient):
    # nunca se llamó a /google/login: no hay cookie `mc_oauth_state`.
    r = await client.get(
        "/api/v1/auth/google/callback", params={"code": "abc123", "state": "made-up"}
    )
    assert r.status_code == 302
    assert "error=google_auth_failed" in r.headers["location"]


async def test_state_mismatch_redirects_with_error(client: httpx.AsyncClient):
    await _start_flow(client)  # deja la cookie mc_oauth_state seteada
    r = await client.get(
        "/api/v1/auth/google/callback",
        params={"code": "abc123", "state": "no-coincide-con-la-cookie"},
    )
    assert r.status_code == 302
    assert "error=google_auth_failed" in r.headers["location"]


async def test_invalid_id_token_redirects_with_error(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        "app.api.routes.auth.exchange_code_for_tokens",
        lambda code, code_verifier: {"id_token": "fake-id-token"},
    )

    def _raise(id_token):
        raise InvalidGoogleTokenError("firma inválida")

    monkeypatch.setattr("app.api.routes.auth.verify_google_id_token", _raise)

    state = await _start_flow(client)
    r = await client.get("/api/v1/auth/google/callback", params={"code": "abc123", "state": state})
    assert r.status_code == 302
    assert "error=google_auth_failed" in r.headers["location"]


async def test_suspended_account_redirects_with_error(
    client: httpx.AsyncClient, session, monkeypatch: pytest.MonkeyPatch
):
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
    admin_token = create_access_token(admin.id, admin.role)

    register = await client.post(
        "/api/v1/auth/register",
        json={
            "first_name": "Gustavo",
            "last_name": "Pérez",
            "email": "gustavo@morficenter.test",
            "password": "cliente123",
        },
    )
    target_id = register.json()["user"]["id"]
    await client.patch(
        f"/api/v1/users/{target_id}",
        json={"status": "SUSPENDED"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    _mock_google(monkeypatch)
    state = await _start_flow(client)
    r = await client.get("/api/v1/auth/google/callback", params={"code": "abc123", "state": state})
    assert r.status_code == 302
    assert "error=google_auth_failed" in r.headers["location"]
