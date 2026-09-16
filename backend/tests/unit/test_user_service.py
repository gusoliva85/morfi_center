import pytest

from app.services.user_service import is_valid_email, is_valid_name, normalize_email, validate_password


def test_normalize_email_strips_whitespace():
    assert normalize_email("  test@test.com  ") == "test@test.com"


def test_normalize_email_lowercases():
    assert normalize_email("Test@TEST.com") == "test@test.com"


@pytest.mark.parametrize(
    "email",
    [
        "user@example.com",
        "user.name+tag@example.co.ar",
        "a@b.co",
    ],
)
def test_valid_emails(email):
    assert is_valid_email(email) is True


@pytest.mark.parametrize(
    "email",
    [
        "",
        "notanemail",
        "missing-at.com",
        "user@",
        "@example.com",
        "user @example.com",
        "user@example",
    ],
)
def test_invalid_emails(email):
    assert is_valid_email(email) is False


@pytest.mark.parametrize(
    "password",
    [
        "abcdefg1",
        "Password123",
        "12345678a",
    ],
)
def test_valid_passwords(password):
    assert validate_password(password) is True


@pytest.mark.parametrize(
    "password",
    [
        "",
        "short1",
        "12345678",
        "abcdefgh",
        "abc123",
        "a1" * 40,  # 80 bytes: supera el limite duro de bcrypt (72 bytes)
    ],
)
def test_invalid_passwords(password):
    assert validate_password(password) is False


def test_password_of_exactly_72_bytes_is_valid():
    password = "a1" * 36  # exactamente 72 bytes
    assert len(password.encode("utf-8")) == 72
    assert validate_password(password) is True


def test_password_of_73_bytes_is_invalid():
    password = "a1" * 36 + "a"  # 73 bytes
    assert len(password.encode("utf-8")) == 73
    assert validate_password(password) is False


@pytest.mark.parametrize("name", ["Juan", "María José", "O'Connor"])
def test_valid_names(name):
    assert is_valid_name(name) is True


@pytest.mark.parametrize("name", ["", "   ", None])
def test_invalid_names(name):
    assert is_valid_name(name) is False
