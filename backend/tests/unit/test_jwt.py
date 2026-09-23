from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.core.config import settings
from app.core.errors import TokenExpiredError, TokenInvalidError
from app.core.security import create_access_token, create_refresh_token, decode_token


class FakeUser:
    """No depende del modelo User real (Fase 1, T-1.2.1) — todavía no existe."""

    def __init__(self, id: int, role: str) -> None:
        self.id = id
        self.role = role


def test_access_token_decodes_with_expected_claims():
    user = FakeUser(id=5, role="CUSTOMER")
    token = create_access_token(user)
    payload = decode_token(token)
    assert payload["sub"] == "5"
    assert payload["role"] == "CUSTOMER"
    assert payload["type"] == "access"


def test_refresh_token_decodes_with_expected_claims():
    user = FakeUser(id=7, role="ADMIN")
    token = create_refresh_token(user)
    payload = decode_token(token)
    assert payload["sub"] == "7"
    assert payload["type"] == "refresh"
    assert "jti" in payload
    assert "role" not in payload  # el refresh no necesita llevar el rol


def test_two_refresh_tokens_have_different_jti():
    user = FakeUser(id=1, role="CUSTOMER")
    jti_1 = decode_token(create_refresh_token(user))["jti"]
    jti_2 = decode_token(create_refresh_token(user))["jti"]
    assert jti_1 != jti_2


def test_expired_token_raises_token_expired_error():
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "1",
        "type": "access",
        "iat": now - timedelta(minutes=20),
        "exp": now - timedelta(minutes=5),
    }
    expired_token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    with pytest.raises(TokenExpiredError):
        decode_token(expired_token)


def test_token_with_wrong_signature_raises_token_invalid_error():
    token = create_access_token(FakeUser(id=1, role="CUSTOMER"))
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
    with pytest.raises(TokenInvalidError):
        decode_token(tampered)


def test_malformed_token_raises_token_invalid_error():
    with pytest.raises(TokenInvalidError):
        decode_token("esto-no-es-un-jwt")
