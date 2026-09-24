import json

import pytest
from sqlalchemy import select, text

from app.core.enums import Role, SettingKey
from app.core.security import create_access_token, hash_password
from app.models import AuditLog, SystemSetting, User
from app.repositories.user_repository import UserRepository

SETTINGS = "/api/v1/settings"

TRANSFER = {"alias": "MI.ALIAS", "holder": "Ana Pérez", "bank": "Banco Ejemplo", "cbu": "1" * 22}


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def make_user(session):
    def make(role: Role, email: str) -> User:
        user = UserRepository(session).create(
            first_name="Test",
            last_name=role.value.title(),
            email=email,
            password_hash=hash_password("secreta123"),
            role=role,
        )
        session.flush()
        return user

    return make


@pytest.fixture()
def admin(make_user):
    return make_user(Role.ADMIN, "admin@example.com")


@pytest.fixture()
def admin_token(admin):
    return create_access_token(admin)


def audit_rows(session) -> list[AuditLog]:
    return list(session.scalars(select(AuditLog).where(AuditLog.entity_type == "setting")))


# ---------- permisos ----------


@pytest.mark.parametrize("role", [Role.CUSTOMER, Role.DELIVERY])
async def test_only_an_admin_can_read_the_settings(client, make_user, role):
    token = create_access_token(make_user(role, "otro@example.com"))

    response = await client.get(SETTINGS, headers=auth(token))

    assert response.status_code == 403


@pytest.mark.parametrize("role", [Role.CUSTOMER, Role.DELIVERY])
async def test_only_an_admin_can_change_a_setting(client, session, make_user, role):
    token = create_access_token(make_user(role, "otro@example.com"))

    response = await client.put(
        f"{SETTINGS}/payment.transfer", json={"value": TRANSFER}, headers=auth(token)
    )

    assert response.status_code == 403
    assert session.scalars(select(SystemSetting)).all() == []  # y no se guardó nada


async def test_without_a_session_both_endpoints_answer_401(client):
    assert (await client.get(SETTINGS)).status_code == 401
    assert (await client.put(f"{SETTINGS}/timezone", json={"value": "UTC"})).status_code == 401


# ---------- GET ----------


async def test_the_listing_has_every_known_key_from_day_one(client, admin_token):
    response = await client.get(SETTINGS, headers=auth(admin_token))

    assert response.status_code == 200
    items = response.json()["items"]
    assert {item["key"] for item in items} == {key.value for key in SettingKey}
    assert all(item["is_default"] for item in items)
    assert all(item["description"] for item in items)


async def test_the_listing_exposes_default_values_and_their_types(client, admin_token):
    items = (await client.get(SETTINGS, headers=auth(admin_token))).json()["items"]
    by_key = {item["key"]: item for item in items}

    assert by_key["stock.reservation_ttl_min"]["value"] == 40
    assert by_key["stock.reservation_ttl_min"]["value_type"] == "int"
    assert by_key["timezone"]["value_type"] == "string"
    assert by_key["shift.default"]["value_type"] == "json"
    assert by_key["shift.default"]["value"]["close"] == "12:00"
    assert by_key["timezone"]["updated_at"] is None


async def test_the_listing_does_not_write_the_defaults(client, session, admin_token):
    await client.get(SETTINGS, headers=auth(admin_token))

    assert session.scalars(select(SystemSetting)).all() == []


async def test_a_saved_key_shows_its_value_and_is_no_longer_a_default(client, admin_token, admin):
    await client.put(
        f"{SETTINGS}/payment.transfer", json={"value": TRANSFER}, headers=auth(admin_token)
    )

    items = (await client.get(SETTINGS, headers=auth(admin_token))).json()["items"]
    saved = next(item for item in items if item["key"] == "payment.transfer")

    assert saved["value"] == TRANSFER
    assert saved["is_default"] is False
    assert saved["updated_by"] == admin.id
    assert saved["updated_at"]


# ---------- PUT ----------


async def test_the_admin_updates_the_transfer_data(client, session, admin_token):
    """El caso del roadmap."""
    response = await client.put(
        f"{SETTINGS}/payment.transfer", json={"value": TRANSFER}, headers=auth(admin_token)
    )

    assert response.status_code == 200
    assert response.json()["value"] == TRANSFER
    stored = session.get(SystemSetting, "payment.transfer")
    assert json.loads(stored.value) == TRANSFER


async def test_put_answers_with_the_canonical_value(client, admin_token):
    """Lo que vuelve es lo guardado (sin espacios, días ordenados), así el front
    muestra lo que realmente quedó."""
    response = await client.put(
        f"{SETTINGS}/payment.transfer",
        json={"value": {**TRANSFER, "alias": "  MI.ALIAS  "}},
        headers=auth(admin_token),
    )

    assert response.json()["value"]["alias"] == "MI.ALIAS"


async def test_a_scalar_setting_can_be_updated(client, admin_token):
    response = await client.put(
        f"{SETTINGS}/stock.reservation_ttl_min", json={"value": 25}, headers=auth(admin_token)
    )

    assert response.status_code == 200
    body = response.json()
    assert (body["value"], body["value_type"], body["is_default"]) == (25, "int", False)


async def test_updating_leaves_an_audit_trail_with_before_and_after(
    client, session, admin, admin_token
):
    await client.put(
        f"{SETTINGS}/stock.reservation_ttl_min", json={"value": 25}, headers=auth(admin_token)
    )

    (entry,) = audit_rows(session)
    assert entry.action == "setting.update"
    assert entry.entity_id == "stock.reservation_ttl_min"
    assert entry.actor_id == admin.id
    assert entry.ip
    assert json.loads(entry.data) == {"before": 40, "after": 25}  # 40 era el default


async def test_the_second_change_records_the_previous_stored_value(client, session, admin_token):
    for minutes in (25, 30):
        await client.put(
            f"{SETTINGS}/stock.reservation_ttl_min",
            json={"value": minutes},
            headers=auth(admin_token),
        )

    last = audit_rows(session)[-1]
    assert json.loads(last.data) == {"before": 25, "after": 30}


async def test_saving_the_value_that_already_rules_changes_and_audits_nothing(
    client, session, admin_token
):
    response = await client.put(
        f"{SETTINGS}/stock.reservation_ttl_min", json={"value": 40}, headers=auth(admin_token)
    )

    assert response.status_code == 200
    assert audit_rows(session) == []
    assert session.scalars(select(SystemSetting)).all() == []


# ---------- PUT inválido ----------


async def test_an_invalid_value_answers_422_with_the_offending_field(client, admin_token):
    response = await client.put(
        f"{SETTINGS}/payment.transfer",
        json={"value": {**TRANSFER, "cbu": "123"}},
        headers=auth(admin_token),
    )

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["details"]["fields"] == [
        {"field": "cbu", "message": "El CBU/CVU debe tener 22 dígitos."}
    ]


async def test_an_invalid_value_saves_and_audits_nothing(client, session, admin_token):
    await client.put(
        f"{SETTINGS}/stock.reservation_ttl_min", json={"value": 0}, headers=auth(admin_token)
    )

    assert session.scalars(select(SystemSetting)).all() == []
    assert audit_rows(session) == []


async def test_an_unknown_key_answers_404(client, admin_token):
    response = await client.put(
        f"{SETTINGS}/no.existe", json={"value": 1}, headers=auth(admin_token)
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.parametrize("body", [{}, {"valor": 1}, {"value": None}])
async def test_a_body_without_a_usable_value_is_rejected(client, admin_token, body):
    response = await client.put(
        f"{SETTINGS}/stock.reservation_ttl_min", json=body, headers=auth(admin_token)
    )

    assert response.status_code == 422


# ---------- dato dañado ----------


async def test_a_corrupt_setting_is_visible_and_repairable_from_the_panel(
    client, session, admin_token
):
    session.execute(
        text(
            "INSERT INTO system_settings (key, value, value_type, updated_at) "
            "VALUES ('timezone', 'no es json', 'string', CURRENT_TIMESTAMP)"
        )
    )

    listing = await client.get(SETTINGS, headers=auth(admin_token))
    assert listing.status_code == 200  # el listado no se rompe
    shown = next(i for i in listing.json()["items"] if i["key"] == "timezone")
    assert shown["value"] == "no es json"

    repaired = await client.put(
        f"{SETTINGS}/timezone", json={"value": "America/Montevideo"}, headers=auth(admin_token)
    )
    assert repaired.status_code == 200
    assert repaired.json()["value"] == "America/Montevideo"
