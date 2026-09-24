import json
from datetime import UTC, date, datetime

import pytest
from sqlalchemy import select

from app.api.routes import shift as shift_routes
from app.core.enums import Role, ShiftStatus
from app.core.security import create_access_token, hash_password
from app.models import AuditLog, Shift, User
from app.repositories.shift_repository import ShiftRepository
from app.repositories.user_repository import UserRepository
from app.services import shift_service
from app.services.settings_service import SettingsService

SHIFT = "/api/v1/shift"
CURRENT = f"{SHIFT}/current"

# Jueves 24/09/2026, turno 08:00-12:00 en Buenos Aires = 11:00Z - 15:00Z.
BEFORE_OPEN = datetime(2026, 9, 24, 10, 0, tzinfo=UTC)  # 07:00 locales
JUST_OPENED = datetime(2026, 9, 24, 11, 0, 30, tzinfo=UTC)  # 08:00:30 locales
DURING = datetime(2026, 9, 24, 13, 7, 30, tzinfo=UTC)  # 10:07:30 locales
AFTER_CLOSE = datetime(2026, 9, 24, 16, 30, tzinfo=UTC)


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
def h(admin):
    """Headers de un admin."""
    return auth(create_access_token(admin))


@pytest.fixture()
def at(monkeypatch):
    def pin(moment: datetime) -> None:
        monkeypatch.setattr(shift_routes, "now_utc", lambda: moment)

    return pin


async def today_shift_id(client, session) -> int:
    """El home crea el turno de hoy al consultarlo."""
    await client.get(CURRENT)
    return session.scalars(select(Shift)).one().id


def audit_rows(session) -> list[AuditLog]:
    return list(session.scalars(select(AuditLog).where(AuditLog.entity_type == "shift")))


# ---------- permisos ----------


@pytest.mark.parametrize("role", [Role.CUSTOMER, Role.DELIVERY])
async def test_only_an_admin_can_use_the_admin_endpoints(client, session, at, make_user, role):
    at(DURING)
    shift_id = await today_shift_id(client, session)
    other = auth(create_access_token(make_user(role, "otro@example.com")))

    assert (await client.get(SHIFT, headers=other)).status_code == 403
    patch = await client.patch(f"{SHIFT}/{shift_id}", json={"prep_eta": "12:20"}, headers=other)
    assert patch.status_code == 403
    move = await client.post(
        f"{SHIFT}/{shift_id}/transition", json={"action": "close"}, headers=other
    )
    assert move.status_code == 403
    assert session.scalars(select(Shift)).one().prep_eta == "12:15"  # nada cambió


async def test_without_a_session_the_admin_endpoints_answer_401(client):
    assert (await client.get(SHIFT)).status_code == 401
    assert (await client.patch(f"{SHIFT}/1", json={})).status_code == 401
    assert (await client.post(f"{SHIFT}/1/transition", json={"action": "close"})).status_code == 401


# ---------- GET /shift ----------


async def test_opening_the_panel_creates_todays_shift(client, session, at, h):
    at(DURING)

    response = await client.get(SHIFT, headers=h)

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"items", "page", "page_size", "total"}
    assert body["total"] == 1
    item = body["items"][0]
    assert item["service_date"] == "2026-09-24"
    assert item["status"] == "OPEN"
    assert item["ordering_open"] is True
    assert (item["open_time"], item["close_time"]) == ("08:00", "12:00")
    assert item["close_at"] == "2026-09-24T15:00:00Z"
    assert item["cancel_deadline"] == "2026-09-24T14:40:00Z"
    assert item["closed_effects_applied_at"] is None


async def test_the_listing_orders_newest_first_and_filters_by_date(client, session, at, h):
    at(DURING)
    template = SettingsService(session).get_shift_default()
    repo = ShiftRepository(session)
    repo.create_from_default(date(2026, 9, 22), template)
    repo.create_from_default(date(2026, 9, 23), template)

    everything = (await client.get(SHIFT, headers=h)).json()
    assert [i["service_date"] for i in everything["items"]] == [
        "2026-09-24",
        "2026-09-23",
        "2026-09-22",
    ]

    one_day = (await client.get(f"{SHIFT}?date=2026-09-23", headers=h)).json()
    assert [i["service_date"] for i in one_day["items"]] == ["2026-09-23"]
    assert one_day["total"] == 1

    none = (await client.get(f"{SHIFT}?date=2026-01-01", headers=h)).json()
    assert (none["items"], none["total"]) == ([], 0)


async def test_the_listing_is_paginated(client, session, at, h):
    at(DURING)
    template = SettingsService(session).get_shift_default()
    for day in (21, 22, 23):
        ShiftRepository(session).create_from_default(date(2026, 9, day), template)

    page = (await client.get(f"{SHIFT}?page=2&page_size=2", headers=h)).json()

    assert page["total"] == 4
    assert [i["service_date"] for i in page["items"]] == ["2026-09-22", "2026-09-21"]


async def test_an_invalid_date_filter_is_rejected(client, h):
    response = await client.get(f"{SHIFT}?date=ayer", headers=h)

    assert response.status_code == 422


async def test_the_listing_shows_the_full_lifecycle_status(client, session, at, h):
    at(DURING)
    shift_id = await today_shift_id(client, session)
    ShiftRepository(session).set_status(session.get(Shift, shift_id), ShiftStatus.IN_PRODUCTION)

    item = (await client.get(SHIFT, headers=h)).json()["items"][0]

    assert item["status"] == "IN_PRODUCTION"
    assert item["ordering_open"] is False


# ---------- PATCH /shift/{id} ----------


async def test_the_admin_moves_the_closing_earlier_and_the_home_reflects_it(client, session, at, h):
    """El caso del roadmap."""
    at(DURING)  # 10:07 locales
    shift_id = await today_shift_id(client, session)

    response = await client.patch(f"{SHIFT}/{shift_id}", json={"close_time": "11:00"}, headers=h)

    assert response.status_code == 200
    assert response.json()["close_time"] == "11:00"
    current = (await client.get(CURRENT)).json()
    assert current["close_time"] == "11:00"
    assert current["close_at"] == "2026-09-24T14:00:00Z"
    assert current["seconds_to_close"] == 3150  # 13:07:30Z -> 14:00:00Z (52 min 30 s)
    assert current["status"] == "OPEN"


async def test_moving_the_closing_before_now_closes_the_shift(client, session, at, h):
    at(DURING)  # 10:07 locales
    shift_id = await today_shift_id(client, session)

    await client.patch(f"{SHIFT}/{shift_id}", json={"close_time": "09:00"}, headers=h)

    current = (await client.get(CURRENT)).json()
    assert (current["status"], current["ordering_open"]) == ("CLOSED", False)


async def test_a_patch_only_changes_what_it_sends(client, session, at, h):
    at(DURING)
    shift_id = await today_shift_id(client, session)

    body = (await client.patch(f"{SHIFT}/{shift_id}", json={"prep_eta": "12:40"}, headers=h)).json()

    assert body["prep_eta"] == "12:40"
    assert (body["open_time"], body["close_time"], body["cancel_window_min"]) == (
        "08:00",
        "12:00",
        20,
    )
    assert body["dispatch_eta"] == "12:30"


async def test_an_estimate_can_be_cleared_with_null(client, session, at, h):
    at(DURING)
    shift_id = await today_shift_id(client, session)

    body = (await client.patch(f"{SHIFT}/{shift_id}", json={"prep_eta": None}, headers=h)).json()

    assert body["prep_eta"] is None


async def test_the_cancel_window_can_be_changed(client, session, at, h):
    at(DURING)
    shift_id = await today_shift_id(client, session)

    body = (
        await client.patch(f"{SHIFT}/{shift_id}", json={"cancel_window_min": 45}, headers=h)
    ).json()

    assert body["cancel_window_min"] == 45
    assert body["cancel_deadline"] == "2026-09-24T14:15:00Z"  # 15:00Z menos 45 min


@pytest.mark.parametrize(
    ("body", "field"),
    [
        ({"close_time": "07:00"}, "value"),  # cierra antes de abrir (regla cruzada)
        ({"close_time": "8am"}, "close_time"),
        ({"open_time": "25:00"}, "open_time"),
        ({"cancel_window_min": 999}, "value"),  # más larga que el turno
        ({"cancel_window_min": -1}, "cancel_window_min"),
        ({"cancel_window_min": "20"}, "cancel_window_min"),
        ({"prep_eta": "tarde"}, "prep_eta"),
        ({"close_time": None}, "close_time"),  # el cierre no es opcional
    ],
)
async def test_an_invalid_schedule_is_rejected_and_nothing_changes(
    client, session, at, h, body, field
):
    at(DURING)
    shift_id = await today_shift_id(client, session)

    response = await client.patch(f"{SHIFT}/{shift_id}", json=body, headers=h)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert field in {f["field"] for f in error["details"]["fields"]}
    shift = session.scalars(select(Shift)).one()
    assert (shift.open_time, shift.close_time, shift.cancel_window_min) == ("08:00", "12:00", 20)
    assert audit_rows(session) == []


async def test_an_unknown_field_is_rejected(client, session, at, h):
    at(DURING)
    shift_id = await today_shift_id(client, session)

    response = await client.patch(f"{SHIFT}/{shift_id}", json={"status": "FINISHED"}, headers=h)

    assert response.status_code == 422


async def test_a_patch_leaves_an_audit_trail_with_only_the_changed_fields(
    client, session, at, h, admin
):
    at(DURING)
    shift_id = await today_shift_id(client, session)

    await client.patch(
        f"{SHIFT}/{shift_id}", json={"close_time": "11:00", "prep_eta": "12:15"}, headers=h
    )

    (entry,) = audit_rows(session)
    assert entry.action == "shift.update"
    assert entry.actor_id == admin.id
    assert entry.entity_id == str(shift_id)
    assert entry.ip
    # prep_eta se mandó igual a como estaba: no cuenta como cambio.
    assert json.loads(entry.data) == {
        "before": {"close_time": "12:00"},
        "after": {"close_time": "11:00"},
    }


@pytest.mark.parametrize("body", [{}, {"close_time": "12:00"}])
async def test_a_patch_that_changes_nothing_audits_nothing(client, session, at, h, body):
    at(DURING)
    shift_id = await today_shift_id(client, session)

    response = await client.patch(f"{SHIFT}/{shift_id}", json=body, headers=h)

    assert response.status_code == 200
    assert audit_rows(session) == []


async def test_a_patch_of_an_unknown_shift_answers_404(client, h):
    response = await client.patch(f"{SHIFT}/999", json={"prep_eta": "12:20"}, headers=h)

    assert response.status_code == 404


async def test_after_the_closing_effects_ran_the_schedule_is_locked(client, session, at, h):
    """Reabrir no deshace lo que el cierre ya hizo (stock congelado, etc.)."""
    at(AFTER_CLOSE)
    shift_id = await today_shift_id(client, session)  # esta visita aplica el cierre

    response = await client.patch(f"{SHIFT}/{shift_id}", json={"close_time": "18:00"}, headers=h)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVALID_TRANSITION"
    assert session.scalars(select(Shift)).one().close_time == "12:00"


async def test_after_the_closing_the_estimates_can_still_be_corrected(client, session, at, h):
    at(AFTER_CLOSE)
    shift_id = await today_shift_id(client, session)

    response = await client.patch(f"{SHIFT}/{shift_id}", json={"prep_eta": "13:00"}, headers=h)

    assert response.status_code == 200
    assert response.json()["prep_eta"] == "13:00"


async def test_a_closed_shift_whose_effects_never_ran_can_still_be_reopened(client, session, at, h):
    """Si nadie miró el turno desde que cerró, los efectos todavía no se aplicaron
    y el admin puede corregir la hora de cierre."""
    at(DURING)
    shift_id = await today_shift_id(client, session)
    await client.patch(f"{SHIFT}/{shift_id}", json={"close_time": "09:00"}, headers=h)
    # No se consultó /current desde que cerró (esa consulta aplicaría el cierre).

    response = await client.patch(f"{SHIFT}/{shift_id}", json={"close_time": "12:00"}, headers=h)

    assert response.status_code == 200
    assert response.json()["status"] == "OPEN"


# ---------- POST /shift/{id}/transition ----------


async def test_closing_now_moves_the_closing_to_the_current_minute(client, session, at, h):
    at(DURING)  # 10:07:30 locales
    shift_id = await today_shift_id(client, session)

    response = await client.post(
        f"{SHIFT}/{shift_id}/transition", json={"action": "close"}, headers=h
    )

    assert response.status_code == 200
    body = response.json()
    assert body["close_time"] == "10:07"
    assert body["status"] == "CLOSED"
    assert body["ordering_open"] is False
    assert body["closed_effects_applied_at"] == "2026-09-24T13:07:30Z"  # se aplicó en el acto
    assert (await client.get(CURRENT)).json()["status"] == "CLOSED"


async def test_closing_now_applies_the_closing_effects_once(client, session, at, h, monkeypatch):
    calls: list[int] = []
    monkeypatch.setattr(shift_service, "_CLOSE_EFFECTS", [lambda ss, s: calls.append(s.id)])
    at(DURING)
    shift_id = await today_shift_id(client, session)

    await client.post(f"{SHIFT}/{shift_id}/transition", json={"action": "close"}, headers=h)
    await client.get(CURRENT)

    assert calls == [shift_id]


async def test_opening_now_moves_the_opening_to_the_current_minute(client, session, at, h):
    at(BEFORE_OPEN)  # 07:00 locales, todavía no abrió
    shift_id = await today_shift_id(client, session)

    response = await client.post(
        f"{SHIFT}/{shift_id}/transition", json={"action": "open"}, headers=h
    )

    body = response.json()
    assert (body["open_time"], body["status"], body["ordering_open"]) == ("07:00", "OPEN", True)
    assert (await client.get(CURRENT)).json()["ordering_open"] is True


async def test_the_transitions_leave_an_audit_trail(client, session, at, h, admin):
    at(BEFORE_OPEN)
    shift_id = await today_shift_id(client, session)
    await client.post(f"{SHIFT}/{shift_id}/transition", json={"action": "open"}, headers=h)
    at(DURING)
    await client.post(f"{SHIFT}/{shift_id}/transition", json={"action": "close"}, headers=h)

    opened, closed = audit_rows(session)
    assert opened.action == "shift.open"
    assert json.loads(opened.data) == {
        "before": {"open_time": "08:00"},
        "after": {"open_time": "07:00"},
    }
    assert closed.action == "shift.close"
    assert json.loads(closed.data) == {
        "before": {"close_time": "12:00"},
        "after": {"close_time": "10:07"},
    }
    assert closed.actor_id == admin.id


@pytest.mark.parametrize(
    ("now", "action"),
    [
        (DURING, "open"),  # ya está abierto
        (AFTER_CLOSE, "open"),  # ya cerró
        (AFTER_CLOSE, "close"),  # ya cerró
        (BEFORE_OPEN, "close"),  # todavía no abrió
        (JUST_OPENED, "close"),  # abrió hace segundos: cerraría en el mismo minuto
    ],
)
async def test_a_transition_that_makes_no_sense_is_rejected(client, session, at, h, now, action):
    at(now)
    shift_id = await today_shift_id(client, session)
    before = (
        session.scalars(select(Shift)).one().close_time,
        session.scalars(select(Shift)).one().open_time,
    )

    response = await client.post(
        f"{SHIFT}/{shift_id}/transition", json={"action": action}, headers=h
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVALID_TRANSITION"
    shift = session.scalars(select(Shift)).one()
    assert (shift.close_time, shift.open_time) == before  # no se tocó nada
    assert audit_rows(session) == []


async def test_only_todays_shift_can_be_opened_or_closed(client, session, at, h):
    at(DURING)
    yesterday = ShiftRepository(session).create_from_default(
        date(2026, 9, 23), SettingsService(session).get_shift_default()
    )

    response = await client.post(
        f"{SHIFT}/{yesterday.id}/transition", json={"action": "close"}, headers=h
    )

    assert response.status_code == 409


async def test_to_production_after_closing(client, session, at, h):
    at(AFTER_CLOSE)
    shift_id = await today_shift_id(client, session)

    response = await client.post(
        f"{SHIFT}/{shift_id}/transition", json={"action": "to_production"}, headers=h
    )

    assert response.status_code == 200
    assert response.json()["status"] == "IN_PRODUCTION"
    (entry,) = audit_rows(session)
    assert entry.action == "shift.to_production"


async def test_to_production_is_rejected_while_orders_are_still_open(client, session, at, h):
    at(DURING)
    shift_id = await today_shift_id(client, session)

    response = await client.post(
        f"{SHIFT}/{shift_id}/transition", json={"action": "to_production"}, headers=h
    )

    assert response.status_code == 409


async def test_a_shift_in_production_accepts_no_more_transitions(client, session, at, h):
    at(AFTER_CLOSE)
    shift_id = await today_shift_id(client, session)
    await client.post(f"{SHIFT}/{shift_id}/transition", json={"action": "to_production"}, headers=h)

    for action in ("open", "close", "to_production"):
        response = await client.post(
            f"{SHIFT}/{shift_id}/transition", json={"action": action}, headers=h
        )
        assert response.status_code == 409


async def test_an_unknown_action_or_shift_is_rejected(client, session, at, h):
    at(DURING)
    shift_id = await today_shift_id(client, session)

    bad_action = await client.post(
        f"{SHIFT}/{shift_id}/transition", json={"action": "explotar"}, headers=h
    )
    bad_shift = await client.post(f"{SHIFT}/999/transition", json={"action": "close"}, headers=h)

    assert bad_action.status_code == 422
    assert bad_shift.status_code == 404
