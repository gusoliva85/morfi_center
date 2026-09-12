"""`google_oauth.build_authorization_redirect` (`03_Roadmap.md` T-1.8.1)."""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import jwt
import pytest
from authlib.oauth2.rfc7636 import create_s256_code_challenge

from app.core.config import settings
from app.services.external import google_oauth


@pytest.fixture(autouse=True)
def _google_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "google_client_id", "test-client-id.apps.googleusercontent.com")
    monkeypatch.setattr(settings, "google_client_secret", "test-client-secret")
    monkeypatch.setattr(
        settings, "google_redirect_uri", "http://localhost:8000/api/v1/auth/google/callback"
    )


def test_redirect_url_points_to_google_authorization_endpoint():
    url, _ = google_oauth.build_authorization_redirect()
    parsed = urlparse(url)
    assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == (
        google_oauth.GOOGLE_AUTHORIZATION_ENDPOINT
    )


def test_redirect_url_has_the_expected_query_params():
    url, _ = google_oauth.build_authorization_redirect()
    params = parse_qs(urlparse(url).query)

    assert params["client_id"] == [settings.google_client_id]
    assert params["redirect_uri"] == [settings.google_redirect_uri]
    assert params["response_type"] == ["code"]
    assert params["scope"] == [google_oauth.GOOGLE_SCOPE]
    assert params["code_challenge_method"] == ["S256"]
    assert "state" in params
    assert "code_challenge" in params


def test_state_cookie_matches_the_url_state_and_code_challenge():
    url, signed_cookie = google_oauth.build_authorization_redirect()
    params = parse_qs(urlparse(url).query)

    payload = jwt.decode(signed_cookie, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    assert payload["state"] == params["state"][0]
    assert create_s256_code_challenge(payload["code_verifier"]) == params["code_challenge"][0]


def test_each_call_generates_a_fresh_state_and_verifier():
    _, cookie_1 = google_oauth.build_authorization_redirect()
    _, cookie_2 = google_oauth.build_authorization_redirect()

    payload_1 = jwt.decode(cookie_1, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    payload_2 = jwt.decode(cookie_2, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    assert payload_1["state"] != payload_2["state"]
    assert payload_1["code_verifier"] != payload_2["code_verifier"]
