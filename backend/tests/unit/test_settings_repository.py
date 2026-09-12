"""`SettingsRepository` (`03_Roadmap.md` T-2.1.1)."""

import pytest
from sqlalchemy import select

from app.core.enums import Role, SettingValueType, UserStatus
from app.models.settings import SystemSetting
from app.models.user import User
from app.repositories.settings_repository import SettingsRepository


def _repo(session) -> SettingsRepository:
    return SettingsRepository(session)


def _make_admin(session) -> User:
    admin = User(
        first_name="Root",
        last_name="Admin",
        email="admin@morficenter.test",
        role=Role.ADMIN,
        status=UserStatus.ACTIVE,
    )
    session.add(admin)
    session.flush()
    return admin


# ── get / set: ida y vuelta ────────────────────────────────
def test_set_and_get_a_complex_json_value_round_trips(session):
    tiers = [
        {"max_km": 2, "amount": 100000},
        {"max_km": 4, "amount": 150000},
        {"max_km": 6, "amount": 250000},
    ]
    _repo(session).set("shipping.tiers", tiers)
    assert _repo(session).get("shipping.tiers") == tiers


def test_set_and_get_a_string_value(session):
    _repo(session).set("timezone", "America/Argentina/Buenos_Aires")
    assert _repo(session).get("timezone") == "America/Argentina/Buenos_Aires"


def test_set_and_get_an_int_value(session):
    _repo(session).set("stock.reservation_ttl_min", 40)
    assert _repo(session).get("stock.reservation_ttl_min") == 40


def test_set_and_get_a_bool_value(session):
    _repo(session).set("feature.x_enabled", True)
    assert _repo(session).get("feature.x_enabled") is True


def test_get_missing_key_returns_default(session):
    assert _repo(session).get("no.existe") is None
    assert _repo(session).get("no.existe", default="fallback") == "fallback"


# ── value_type: inferido y explícito ───────────────────────
@pytest.mark.parametrize(
    ("value", "expected_type"),
    [
        (True, SettingValueType.BOOL),
        (40, SettingValueType.INT),
        ("hola", SettingValueType.STRING),
        ({"a": 1}, SettingValueType.JSON),
        ([1, 2, 3], SettingValueType.JSON),
    ],
)
def test_value_type_is_inferred_from_the_python_type(session, value, expected_type):
    row = _repo(session).set("k", value)
    assert row.value_type == expected_type


def test_explicit_value_type_overrides_inference(session):
    row = _repo(session).set("orders.code_prefix", "MC", value_type=SettingValueType.STRING)
    assert row.value_type == SettingValueType.STRING


# ── set: upsert ─────────────────────────────────────────────
def test_set_twice_updates_in_place_without_duplicating(session):
    _repo(session).set("timezone", "America/Argentina/Buenos_Aires")
    _repo(session).set("timezone", "America/Sao_Paulo")

    assert _repo(session).get("timezone") == "America/Sao_Paulo"
    rows = session.scalars(select(SystemSetting).where(SystemSetting.key == "timezone")).all()
    assert len(rows) == 1


def test_set_records_the_actor(session):
    admin = _make_admin(session)
    row = _repo(session).set("timezone", "America/Argentina/Buenos_Aires", actor_id=admin.id)
    assert row.updated_by == admin.id


def test_set_stores_the_description(session):
    row = _repo(session).set("timezone", "x", description="Zona horaria de operación")
    assert row.description == "Zona horaria de operación"


def test_set_updating_without_description_keeps_the_previous_one(session):
    _repo(session).set("timezone", "x", description="Zona horaria de operación")
    row = _repo(session).set("timezone", "y")
    assert row.description == "Zona horaria de operación"


# ── get_typed ───────────────────────────────────────────────
def test_get_typed_returns_the_value_when_type_matches(session):
    _repo(session).set("stock.reservation_ttl_min", 40)
    assert _repo(session).get_typed("stock.reservation_ttl_min", int) == 40


def test_get_typed_returns_default_when_missing(session):
    assert _repo(session).get_typed("no.existe", int, default=99) == 99


def test_get_typed_raises_type_error_on_mismatch(session):
    _repo(session).set("timezone", "America/Argentina/Buenos_Aires")
    with pytest.raises(TypeError):
        _repo(session).get_typed("timezone", int)
