import pytest
from sqlalchemy import text

from app.core.enums import Role, SettingValueType
from app.core.security import hash_password
from app.models import SystemSetting
from app.repositories.settings_repository import SettingsRepository
from app.repositories.user_repository import UserRepository


@pytest.fixture()
def repo(session) -> SettingsRepository:
    return SettingsRepository(session)


@pytest.fixture()
def admin(session):
    user = UserRepository(session).create(
        first_name="Admin",
        last_name="Morfi",
        email="admin@example.com",
        password_hash=hash_password("secreta123"),
        role=Role.ADMIN,
    )
    session.flush()
    return user


def test_get_of_a_missing_key_returns_the_default(repo):
    assert repo.get("no.existe", default="valor_por_defecto") == "valor_por_defecto"


def test_get_without_default_returns_none_for_a_missing_key(repo):
    assert repo.get("no.existe") is None


def test_set_and_get_a_complex_json_value_round_trips(repo):
    """El caso del roadmap: los tiers de envío, un valor JSON anidado real."""
    tiers = [
        {"max_km": 2, "amount": 100000},
        {"max_km": 4, "amount": 150000},
        {"max_km": 6, "amount": 250000},
    ]

    repo.set("shipping.tiers", tiers)

    assert repo.get("shipping.tiers") == tiers


@pytest.mark.parametrize(
    ("value", "expected_type"),
    [
        (40, SettingValueType.INT),
        ("America/Argentina/Buenos_Aires", SettingValueType.STRING),
        (True, SettingValueType.BOOL),
        ({"open": "08:00", "close": "12:00"}, SettingValueType.JSON),
        ([1, 2, 3], SettingValueType.JSON),
    ],
)
def test_set_infers_the_correct_value_type(repo, value, expected_type):
    repo.set("clave.de.prueba", value)

    assert repo.get_typed("clave.de.prueba").value_type == expected_type


def test_bool_is_not_confused_with_int(repo):
    """En Python `isinstance(True, int)` es True — sin el chequeo en orden,
    un booleano quedaría guardado (y mostrado en el admin) como entero."""
    repo.set("clave.bool", True)

    row = repo.get_typed("clave.bool")
    assert row.value_type == SettingValueType.BOOL
    assert repo.get("clave.bool") is True  # no 1


def test_set_updates_an_existing_key_in_place(repo):
    repo.set("timezone", "America/Argentina/Buenos_Aires")
    repo.set("timezone", "America/Montevideo")

    assert repo.get("timezone") == "America/Montevideo"
    assert repo.session.query(SystemSetting).count() == 1  # no duplicó la fila


def test_set_records_who_made_the_change(repo, admin):
    repo.set("payment.transfer", {"alias": "MORFI.CENTER"}, actor=admin)

    assert repo.get_typed("payment.transfer").updated_by == admin.id


def test_set_without_an_actor_leaves_updated_by_null(repo):
    """El seed (T-2.1.4) escribe los defaults sin que ningún admin lo pida."""
    repo.set("orders.code_prefix", "MC")

    assert repo.get_typed("orders.code_prefix").updated_by is None


def test_set_saves_the_description_only_on_creation_by_default(repo):
    repo.set("timezone", "America/Argentina/Buenos_Aires", description="Zona horaria de operación")
    repo.set("timezone", "America/Montevideo")  # sin description: no la borra

    assert repo.get_typed("timezone").description == "Zona horaria de operación"


def test_set_can_update_the_description_explicitly(repo):
    repo.set("timezone", "America/Argentina/Buenos_Aires", description="Original")
    repo.set("timezone", "America/Montevideo", description="Actualizada")

    assert repo.get_typed("timezone").description == "Actualizada"


def test_list_all_returns_every_setting_sorted_by_key(repo):
    repo.set("zeta.clave", 1)
    repo.set("alfa.clave", 2)

    keys = [row.key for row in repo.list_all()]
    assert keys == ["alfa.clave", "zeta.clave"]


def test_the_value_is_stored_as_real_json_text(repo):
    """No un string de Python (con comillas simples): tiene que poder leerlo
    cualquier otra herramienta que hable JSON de verdad."""
    repo.set("coverage.origin", {"lat": -34.63, "lng": -58.41})

    raw = repo.session.execute(
        text("SELECT value FROM system_settings WHERE key = 'coverage.origin'")
    ).scalar_one()
    assert raw == '{"lat": -34.63, "lng": -58.41}'


def test_get_typed_returns_none_for_a_missing_key(repo):
    assert repo.get_typed("no.existe") is None
