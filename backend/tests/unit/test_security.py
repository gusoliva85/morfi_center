"""Hashing de contraseñas y tokens JWT (`03_Roadmap.md` T-1.1.2, T-1.1.3, T-1.9.1)."""

from datetime import timedelta

import jwt as pyjwt
import pytest

from app.core.config import settings
from app.core.security import (
    BCRYPT_ROUNDS,
    TokenExpiredError,
    TokenInvalidError,
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    decode_token,
    hash_password,
    needs_rehash,
    verify_password,
)
from app.core.timezone import now_utc


def test_verify_password_matches_its_own_hash():
    hashed = hash_password("cliente123")
    assert verify_password("cliente123", hashed) is True


def test_verify_password_rejects_wrong_password():
    hashed = hash_password("cliente123")
    assert verify_password("otra-contraseña", hashed) is False


def test_hash_is_not_the_plain_text():
    hashed = hash_password("cliente123")
    assert hashed != "cliente123"
    assert "cliente123" not in hashed


def test_hash_uses_bcrypt_with_configured_cost():
    hashed = hash_password("cliente123")
    assert hashed.startswith(("$2b$", "$2a$", "$2y$"))
    rounds = int(hashed.split("$")[2])
    assert rounds == BCRYPT_ROUNDS
    assert rounds >= 12


def test_same_password_hashes_differently_each_time():
    # bcrypt genera una sal distinta en cada llamada
    assert hash_password("cliente123") != hash_password("cliente123")


def test_hash_password_rejects_empty():
    with pytest.raises(ValueError):
        hash_password("")


@pytest.mark.parametrize("bad", ["", None])
def test_verify_password_with_empty_input_is_false_not_error(bad):
    hashed = hash_password("cliente123")
    assert verify_password(bad, hashed) is False
    assert verify_password("cliente123", bad) is False


def test_verify_password_with_malformed_hash_is_false_not_error():
    assert verify_password("cliente123", "no-es-un-hash-valido") is False


def test_needs_rehash_is_false_for_a_current_hash():
    assert needs_rehash(hash_password("cliente123")) is False


def test_needs_rehash_true_for_lower_cost_hash():
    from passlib.context import CryptContext

    old = CryptContext(schemes=["bcrypt"], bcrypt__rounds=4).hash("cliente123")
    assert needs_rehash(old) is True


# ══════════════════════════════════════════════════════════
#  JWT — access / refresh tokens
# ══════════════════════════════════════════════════════════


def test_access_token_round_trips_with_expected_claims():
    token = create_access_token(42, "ADMIN")
    payload = decode_token(token, expected_type="access")
    assert payload["sub"] == "42"
    assert payload["role"] == "ADMIN"
    assert payload["type"] == "access"
    assert payload["exp"] - payload["iat"] == settings.access_token_minutes * 60


def test_refresh_token_round_trips_with_expected_claims():
    token, jti = create_refresh_token(7)
    payload = decode_token(token, expected_type="refresh")
    assert payload["sub"] == "7"
    assert payload["type"] == "refresh"
    assert payload["jti"] == jti
    assert payload["exp"] - payload["iat"] == settings.refresh_token_days * 86400


def test_refresh_token_jti_is_unique_by_default():
    _, jti1 = create_refresh_token(1)
    _, jti2 = create_refresh_token(1)
    assert jti1 != jti2


def test_refresh_token_accepts_explicit_jti_for_rotation():
    token, jti = create_refresh_token(1, jti="fixed-jti-123")
    assert jti == "fixed-jti-123"
    assert decode_token(token, expected_type="refresh")["jti"] == "fixed-jti-123"


def test_password_reset_token_round_trips_with_expected_claims():
    token, jti = create_password_reset_token(7)
    payload = decode_token(token, expected_type="password_reset")
    assert payload["sub"] == "7"
    assert payload["type"] == "password_reset"
    assert payload["jti"] == jti
    assert payload["exp"] - payload["iat"] == settings.password_reset_token_minutes * 60


def test_password_reset_token_jti_is_unique_by_default():
    _, jti1 = create_password_reset_token(1)
    _, jti2 = create_password_reset_token(1)
    assert jti1 != jti2


def test_password_reset_token_rejected_by_other_token_types():
    token, _ = create_password_reset_token(1)
    with pytest.raises(TokenInvalidError):
        decode_token(token, expected_type="access")
    with pytest.raises(TokenInvalidError):
        decode_token(token, expected_type="refresh")


def test_expired_password_reset_token_raises_token_expired_error():
    stale = now_utc() - timedelta(minutes=settings.password_reset_token_minutes + 1)
    token, _ = create_password_reset_token(1, now=stale)
    with pytest.raises(TokenExpiredError):
        decode_token(token, expected_type="password_reset")


def test_expired_access_token_raises_token_expired_error():
    stale = now_utc() - timedelta(minutes=settings.access_token_minutes + 1)
    token = create_access_token(1, "CUSTOMER", now=stale)
    with pytest.raises(TokenExpiredError):
        decode_token(token, expected_type="access")


def test_expired_refresh_token_raises_token_expired_error():
    stale = now_utc() - timedelta(days=settings.refresh_token_days + 1)
    token, _ = create_refresh_token(1, now=stale)
    with pytest.raises(TokenExpiredError):
        decode_token(token, expected_type="refresh")


def test_token_with_wrong_signature_is_invalid():
    payload = {"sub": "1", "role": "CUSTOMER", "type": "access"}
    forged = pyjwt.encode(
        payload, "otro-secreto-completamente-distinto-0000000000", algorithm=settings.jwt_algorithm
    )
    with pytest.raises(TokenInvalidError):
        decode_token(forged)


def test_malformed_token_string_is_invalid():
    with pytest.raises(TokenInvalidError):
        decode_token("esto-no-es-un-jwt")


def test_token_type_mismatch_is_invalid():
    access = create_access_token(1, "CUSTOMER")
    with pytest.raises(TokenInvalidError):
        decode_token(access, expected_type="refresh")


def test_decode_without_expected_type_accepts_any_type():
    access = create_access_token(1, "CUSTOMER")
    refresh, _ = create_refresh_token(1)
    assert decode_token(access)["type"] == "access"
    assert decode_token(refresh)["type"] == "refresh"
