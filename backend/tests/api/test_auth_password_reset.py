"""Tests de `POST /auth/password/forgot` y `/password/reset` (`03_Roadmap.md` T-1.9.1)."""

from __future__ import annotations

import logging
from datetime import timedelta

import httpx

from app.core.config import settings
from app.core.security import create_password_reset_token
from app.core.timezone import now_utc
from app.repositories.user_repository import UserRepository

VALID = {
    "first_name": "Gustavo",
    "last_name": "Pérez",
    "email": "gustavo@morficenter.test",
    "password": "cliente123",
}


async def _register(client: httpx.AsyncClient) -> None:
    r = await client.post("/api/v1/auth/register", json=VALID)
    assert r.status_code == 201


def _token_from_logs(caplog) -> str:
    for record in caplog.records:
        if "Token de reseteo" in record.getMessage():
            return record.getMessage().rsplit(": ", 1)[-1]
    raise AssertionError("no se logueó ningún token de reseteo")


async def test_forgot_password_always_returns_200_for_known_email(client: httpx.AsyncClient):
    await _register(client)
    r = await client.post("/api/v1/auth/password/forgot", json={"email": VALID["email"]})
    assert r.status_code == 200
    assert r.json() == {"ok": True}


async def test_forgot_password_always_returns_200_for_unknown_email(client: httpx.AsyncClient):
    r = await client.post("/api/v1/auth/password/forgot", json={"email": "nadie@morficenter.test"})
    assert r.status_code == 200
    assert r.json() == {"ok": True}


async def test_forgot_password_logs_the_token_in_dev(client: httpx.AsyncClient, caplog):
    await _register(client)
    with caplog.at_level(logging.INFO, logger="morfi.auth"):
        r = await client.post("/api/v1/auth/password/forgot", json={"email": VALID["email"]})
    assert r.status_code == 200
    assert _token_from_logs(caplog)  # no lanza si no se encontró


async def test_full_reset_flow_changes_the_password(client: httpx.AsyncClient, caplog):
    await _register(client)

    with caplog.at_level(logging.INFO, logger="morfi.auth"):
        forgot = await client.post("/api/v1/auth/password/forgot", json={"email": VALID["email"]})
    assert forgot.status_code == 200
    token = _token_from_logs(caplog)

    reset = await client.post(
        "/api/v1/auth/password/reset", json={"token": token, "password": "nuevaClave123"}
    )
    assert reset.status_code == 200
    assert reset.json() == {"ok": True}

    old_login = await client.post(
        "/api/v1/auth/login", json={"email": VALID["email"], "password": VALID["password"]}
    )
    assert old_login.status_code == 401

    new_login = await client.post(
        "/api/v1/auth/login", json={"email": VALID["email"], "password": "nuevaClave123"}
    )
    assert new_login.status_code == 200


async def test_expired_token_returns_400(client: httpx.AsyncClient, session):
    await _register(client)
    user = UserRepository(session).get_by_email(VALID["email"])
    stale = now_utc() - timedelta(minutes=settings.password_reset_token_minutes + 1)
    token, _jti = create_password_reset_token(user.id, now=stale)

    r = await client.post(
        "/api/v1/auth/password/reset", json={"token": token, "password": "nuevaClave123"}
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "INVALID_INPUT"
    assert r.json()["error"]["details"]["field"] == "token"


async def test_malformed_token_returns_400(client: httpx.AsyncClient):
    r = await client.post(
        "/api/v1/auth/password/reset",
        json={"token": "no-soy-un-jwt", "password": "nuevaClave123"},
    )
    assert r.status_code == 400


async def test_reused_token_returns_400(client: httpx.AsyncClient, caplog):
    await _register(client)
    with caplog.at_level(logging.INFO, logger="morfi.auth"):
        await client.post("/api/v1/auth/password/forgot", json={"email": VALID["email"]})
    token = _token_from_logs(caplog)

    first = await client.post(
        "/api/v1/auth/password/reset", json={"token": token, "password": "nuevaClave123"}
    )
    assert first.status_code == 200

    second = await client.post(
        "/api/v1/auth/password/reset", json={"token": token, "password": "otraClave456"}
    )
    assert second.status_code == 400


async def test_weak_new_password_returns_400(client: httpx.AsyncClient, caplog):
    await _register(client)
    with caplog.at_level(logging.INFO, logger="morfi.auth"):
        await client.post("/api/v1/auth/password/forgot", json={"email": VALID["email"]})
    token = _token_from_logs(caplog)

    r = await client.post("/api/v1/auth/password/reset", json={"token": token, "password": "short"})
    assert r.status_code == 400
    assert r.json()["error"]["details"]["field"] == "password"
