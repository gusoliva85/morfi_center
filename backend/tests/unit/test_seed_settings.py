import pytest
from sqlalchemy import func, select

from app.core.config import settings
from app.core.enums import Role, SettingKey
from app.core.security import create_access_token, hash_password
from app.db.seed import run_seed, seed_system_settings
from app.models import AuditLog, SystemSetting
from app.repositories.user_repository import UserRepository
from app.services.settings_service import SPECS, SettingsService


def count_rows(session) -> int:
    return session.scalar(select(func.count()).select_from(SystemSetting))


def test_the_seed_creates_every_known_setting(session):
    created = seed_system_settings(session)

    assert set(created) == {key.value for key in SettingKey}
    assert count_rows(session) == len(SettingKey)


def test_every_seeded_row_holds_its_default_and_its_description(session):
    seed_system_settings(session)

    for spec in SPECS.values():
        row = session.get(SystemSetting, spec.key.value)
        assert SettingsService(session).repo.get(spec.key.value) == spec.default
        assert row.description == spec.description
        assert row.updated_by is None  # lo escribió el sistema, no un admin


def test_the_seeded_values_read_back_the_same_as_the_unseeded_defaults(session):
    """Materializar los defaults no cambia lo que el resto del sistema ve."""
    service = SettingsService(session)
    before = {key: service.get(key) for key in SettingKey}

    seed_system_settings(session)

    assert {key: service.get(key) for key in SettingKey} == before


def test_running_the_seed_twice_creates_nothing_the_second_time(session):
    seed_system_settings(session)

    assert seed_system_settings(session) == []
    assert count_rows(session) == len(SettingKey)


def test_the_seed_never_overwrites_what_an_admin_changed(session):
    seed_system_settings(session)
    SettingsService(session).set("stock.reservation_ttl_min", 25)

    seed_system_settings(session)

    assert SettingsService(session).get_stock_reservation_ttl_min() == 25


def test_the_seed_fills_only_what_is_missing(session):
    SettingsService(session).set("orders.code_prefix", "PED")

    created = seed_system_settings(session)

    assert "orders.code_prefix" not in created
    assert len(created) == len(SettingKey) - 1
    assert SettingsService(session).get_order_code_prefix() == "PED"


def test_the_seed_leaves_no_audit_trail(session):
    """No es un cambio de nadie: auditarlo llenaría el historial de ruido en
    cada deploy."""
    seed_system_settings(session)

    assert session.scalar(select(func.count()).select_from(AuditLog)) == 0


def test_the_seed_also_runs_in_production(session, monkeypatch):
    """A diferencia de los usuarios de prueba, son valores de negocio y no
    secretos: el servidor real también los necesita."""
    monkeypatch.setattr(settings, "app_env", "production")

    assert len(seed_system_settings(session)) == len(SettingKey)


def test_run_seed_includes_the_settings(session):
    run_seed(session)

    assert count_rows(session) == len(SettingKey)


@pytest.fixture()
def admin_token(session):
    admin = UserRepository(session).create(
        first_name="A",
        last_name="B",
        email="admin@example.com",
        password_hash=hash_password("secreta123"),
        role=Role.ADMIN,
    )
    session.flush()
    return create_access_token(admin)


async def test_after_the_seed_the_api_returns_the_full_set(client, session, admin_token):
    """El caso del roadmap."""
    seed_system_settings(session)

    response = await client.get(
        "/api/v1/settings", headers={"Authorization": f"Bearer {admin_token}"}
    )

    items = response.json()["items"]
    assert {item["key"] for item in items} == {key.value for key in SettingKey}
    assert all(item["is_default"] is False for item in items)  # ya son filas reales
    assert {item["key"]: item["value"] for item in items} == {
        spec.key.value: spec.default for spec in SPECS.values()
    }
