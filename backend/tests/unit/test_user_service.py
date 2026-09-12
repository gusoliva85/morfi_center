"""Reglas de validación de usuario (`03_Roadmap.md` T-1.1.1, T-1.6.1)."""

import pytest

from app.core.enums import Role, UserStatus
from app.core.errors import InvalidInputError
from app.models.user import User
from app.services import user_service as svc


def _make_user() -> User:
    return User(
        first_name="Gustavo",
        last_name="Pérez",
        email="gustavo@morficenter.test",
        phone="1122334455",
        role=Role.CUSTOMER,
        status=UserStatus.ACTIVE,
    )


# ── normalize_email ─────────────────────────────────────
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("juan@gmail.com", "juan@gmail.com"),
        ("  Juan.Perez@Gmail.COM  ", "juan.perez@gmail.com"),
        ("a@b.co", "a@b.co"),
        ("nombre+tag@dominio.com.ar", "nombre+tag@dominio.com.ar"),
    ],
)
def test_normalize_email_valid(raw, expected):
    assert svc.normalize_email(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        None,
        "sin-arroba.com",
        "con espacio@dominio.com",
        "@dominio.com",
        "user@",
        "user@dominio",
    ],
)
def test_normalize_email_invalid(raw):
    with pytest.raises(InvalidInputError) as exc:
        svc.normalize_email(raw)
    assert exc.value.code == "INVALID_INPUT"
    assert exc.value.details["field"] == "email"


# ── validate_person_name ────────────────────────────────
@pytest.mark.parametrize(
    "raw",
    ["Ana", "María José", "O'Connor", "Jean-Paul", "D'Angelo Jr.", "  Gustavo  "],
)
def test_validate_person_name_valid(raw):
    assert svc.validate_person_name(raw) == raw.strip()


@pytest.mark.parametrize(
    "raw",
    ["", "   ", None, "A", "Juan123", "123", "!!!", "x" * 81],
)
def test_validate_person_name_invalid(raw):
    with pytest.raises(InvalidInputError) as exc:
        svc.validate_person_name(raw, field="apellido")
    assert exc.value.details["field"] == "apellido"


# ── normalize_phone ──────────────────────────────────────
def test_normalize_phone_none_and_empty_are_accepted():
    assert svc.normalize_phone(None) is None
    assert svc.normalize_phone("") is None
    assert svc.normalize_phone("   ") is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("+54 11 4444-5555", "+54 11 4444-5555"),
        ("1144445555", "1144445555"),
        ("(011) 4444-5555", "(011) 4444-5555"),
    ],
)
def test_normalize_phone_valid(raw, expected):
    assert svc.normalize_phone(raw) == expected


@pytest.mark.parametrize("raw", ["abc", "123", "+", "11-", "telefono: 12345"])
def test_normalize_phone_invalid(raw):
    with pytest.raises(InvalidInputError) as exc:
        svc.normalize_phone(raw)
    assert exc.value.details["field"] == "phone"


# ── validate_password ────────────────────────────────────
@pytest.mark.parametrize("raw", ["cliente123", "Abcdefg1", "contraseñaSegura9"])
def test_validate_password_valid(raw):
    svc.validate_password(raw)  # no debe lanzar


@pytest.mark.parametrize(
    ("raw", "expected_rules"),
    [
        ("", ["mínimo 8 caracteres", "al menos una letra", "al menos un número"]),
        ("short1", ["mínimo 8 caracteres"]),
        ("12345678", ["al menos una letra"]),
        ("sololetras", ["al menos un número"]),
        (None, ["mínimo 8 caracteres", "al menos una letra", "al menos un número"]),
    ],
)
def test_validate_password_invalid(raw, expected_rules):
    with pytest.raises(InvalidInputError) as exc:
        svc.validate_password(raw)
    assert exc.value.details["field"] == "password"
    assert exc.value.details["requirements_failed"] == expected_rules


# ── update_profile ────────────────────────────────────────
def test_update_profile_applies_only_fields_present_in_updates():
    user = _make_user()
    svc.update_profile(user, {"phone": "1155556666"})
    assert user.phone == "1155556666"
    assert user.first_name == "Gustavo"  # no tocado
    assert user.last_name == "Pérez"  # no tocado


def test_update_profile_updates_first_and_last_name():
    user = _make_user()
    svc.update_profile(user, {"first_name": "Mariana", "last_name": "López"})
    assert user.first_name == "Mariana"
    assert user.last_name == "López"


def test_update_profile_phone_none_clears_it():
    user = _make_user()
    assert user.phone is not None
    svc.update_profile(user, {"phone": None})
    assert user.phone is None


def test_update_profile_empty_updates_changes_nothing():
    user = _make_user()
    svc.update_profile(user, {})
    assert user.first_name == "Gustavo"
    assert user.last_name == "Pérez"
    assert user.phone == "1122334455"


def test_update_profile_invalid_first_name_raises_and_does_not_touch_user():
    user = _make_user()
    with pytest.raises(InvalidInputError) as exc:
        svc.update_profile(user, {"first_name": "123"})
    assert exc.value.details["field"] == "first_name"
    assert user.first_name == "Gustavo"  # sin cambios ante el error


def test_update_profile_invalid_phone_raises():
    user = _make_user()
    with pytest.raises(InvalidInputError) as exc:
        svc.update_profile(user, {"phone": "abc"})
    assert exc.value.details["field"] == "phone"


def test_update_profile_returns_the_same_user_instance():
    user = _make_user()
    result = svc.update_profile(user, {"last_name": "Gómez"})
    assert result is user
