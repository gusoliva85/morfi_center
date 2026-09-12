"""Tests de `GET /api/v1/auth/google/login` (`03_Roadmap.md` T-1.8.1)."""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from app.core.config import settings
from app.services.external.google_oauth import (
    GOOGLE_AUTHORIZATION_ENDPOINT,
    GOOGLE_SCOPE,
    OAUTH_STATE_COOKIE_NAME,
)


@pytest.fixture(autouse=True)
def _google_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "google_client_id", "test-client-id.apps.googleusercontent.com")
    monkeypatch.setattr(settings, "google_client_secret", "test-client-secret")
    monkeypatch.setattr(
        settings, "google_redirect_uri", "http://localhost:8000/api/v1/auth/google/callback"
    )


async def test_redirects_to_google_with_the_expected_params(client: httpx.AsyncClient):
    r = await client.get("/api/v1/auth/google/login")
    assert r.status_code == 302

    location = r.headers["location"]
    parsed = urlparse(location)
    assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == GOOGLE_AUTHORIZATION_ENDPOINT

    params = parse_qs(parsed.query)
    assert params["client_id"] == [settings.google_client_id]
    assert params["redirect_uri"] == [settings.google_redirect_uri]
    assert params["response_type"] == ["code"]
    assert params["scope"] == [GOOGLE_SCOPE]
    assert params["code_challenge_method"] == ["S256"]
    assert "state" in params
    assert "code_challenge" in params


async def test_sets_the_oauth_state_cookie(client: httpx.AsyncClient):
    r = await client.get("/api/v1/auth/google/login")
    assert OAUTH_STATE_COOKIE_NAME in r.cookies


async def test_two_requests_get_different_states(client: httpx.AsyncClient):
    r1 = await client.get("/api/v1/auth/google/login")
    r2 = await client.get("/api/v1/auth/google/login")

    state_1 = parse_qs(urlparse(r1.headers["location"]).query)["state"][0]
    state_2 = parse_qs(urlparse(r2.headers["location"]).query)["state"][0]
    assert state_1 != state_2
