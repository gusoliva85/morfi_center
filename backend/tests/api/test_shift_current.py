from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select

from app.api.routes import shift as shift_routes
from app.core.enums import ShiftStatus
from app.models import Shift
from app.repositories.shift_repository import ShiftRepository
from app.services import shift_service
from app.services.settings_service import SettingsService

CURRENT = "/api/v1/shift/current"

# Jueves 24/09/2026, turno 08:00-12:00 en Buenos Aires = 11:00Z - 15:00Z.
BEFORE_OPEN = datetime(2026, 9, 24, 10, 0, tzinfo=UTC)
DURING = datetime(2026, 9, 24, 13, 0, tzinfo=UTC)
AFTER_CLOSE = datetime(2026, 9, 24, 16, 30, tzinfo=UTC)
SATURDAY = datetime(2026, 9, 26, 13, 0, tzinfo=UTC)


@pytest.fixture()
def at(monkeypatch):
    """Fija la hora del servidor para el endpoint."""

    def pin(moment: datetime) -> None:
        monkeypatch.setattr(shift_routes, "now_utc", lambda: moment)

    return pin


def count_shifts(session) -> int:
    return session.scalar(select(func.count()).select_from(Shift))


# ---------- turno abierto ----------


async def test_an_open_shift_reports_the_time_left(client, at):
    at(DURING)

    response = await client.get(CURRENT)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "OPEN"
    assert body["seconds_to_close"] == 7200  # 13:00Z -> 15:00Z
    assert body["seconds_to_close"] > 0
    assert body["ordering_open"] is True


async def test_the_response_has_the_documented_shape(client, at):
    at(DURING)

    body = (await client.get(CURRENT)).json()

    assert body == {
        "status": "OPEN",
        "now": "2026-09-24T13:00:00Z",
        "ordering_open": True,
        "service_date": "2026-09-24",
        "open_time": "08:00",
        "close_time": "12:00",
        "prep_eta": "12:15",
        "open_at": "2026-09-24T11:00:00Z",
        "close_at": "2026-09-24T15:00:00Z",
        "cancel_deadline": "2026-09-24T14:40:00Z",
        "cancel_deadline_time": "11:40",
        "seconds_to_close": 7200,
    }


async def test_it_is_public_and_needs_no_session(client, at):
    at(DURING)

    response = await client.get(CURRENT)  # sin Authorization

    assert response.status_code == 200


async def test_the_response_is_never_cached(client, at):
    """Lleva la hora del servidor: si un proxy la cacheara sería mentira."""
    at(DURING)

    response = await client.get(CURRENT)

    assert response.headers["cache-control"] == "no-store"


# ---------- antes y después ----------


async def test_before_opening_the_shift_is_scheduled_and_not_orderable(client, at):
    at(BEFORE_OPEN)

    body = (await client.get(CURRENT)).json()

    assert body["status"] == "SCHEDULED"
    assert body["ordering_open"] is False
    assert body["seconds_to_close"] == 18000  # todavía falta el turno entero + la espera


async def test_after_closing_the_shift_is_closed(client, at):
    """El caso del roadmap."""
    at(AFTER_CLOSE)

    body = (await client.get(CURRENT)).json()

    assert body["status"] == "CLOSED"
    assert body["seconds_to_close"] == 0
    assert body["ordering_open"] is False


async def test_the_closing_instant_counts_as_closed(client, at):
    at(datetime(2026, 9, 24, 15, 0, tzinfo=UTC))

    body = (await client.get(CURRENT)).json()

    assert (body["status"], body["seconds_to_close"]) == ("CLOSED", 0)


async def test_now_is_the_server_time(client, at):
    at(DURING)

    assert (await client.get(CURRENT)).json()["now"] == "2026-09-24T13:00:00Z"


async def test_a_shift_sent_to_production_is_no_longer_orderable(client, session, at):
    """Aunque el reloj diga que sigue abierto (el admin ya arrancó a cocinar)."""
    at(DURING)
    await client.get(CURRENT)  # crea el turno de hoy
    shift = session.scalars(select(Shift)).one()
    ShiftRepository(session).set_status(shift, ShiftStatus.IN_PRODUCTION)

    body = (await client.get(CURRENT)).json()

    assert body["status"] == "OPEN"  # lo que dice el reloj
    assert body["ordering_open"] is False


# ---------- crea el turno del día bajo demanda ----------


async def test_the_first_visit_creates_todays_shift_and_the_second_reuses_it(client, session, at):
    at(DURING)

    await client.get(CURRENT)
    await client.get(CURRENT)

    assert count_shifts(session) == 1


async def test_a_non_operating_day_answers_no_service_and_creates_nothing(client, session, at):
    at(SATURDAY)

    response = await client.get(CURRENT)

    assert response.status_code == 200
    assert response.json() == {
        "status": "NO_SERVICE",
        "now": "2026-09-26T13:00:00Z",
        "ordering_open": False,
        "service_date": None,
        "open_time": None,
        "close_time": None,
        "prep_eta": None,
        "open_at": None,
        "close_at": None,
        "cancel_deadline": None,
        "cancel_deadline_time": None,
        "seconds_to_close": None,
    }
    assert count_shifts(session) == 0


async def test_today_is_the_local_date(client, at):
    """23:00 en Buenos Aires ya es viernes en UTC; el turno sigue siendo el del jueves."""
    at(datetime(2026, 9, 25, 2, 0, tzinfo=UTC))

    body = (await client.get(CURRENT)).json()

    assert body["service_date"] == "2026-09-24"
    assert body["status"] == "CLOSED"


async def test_the_shift_reflects_the_template_the_admin_configured(client, session, at):
    SettingsService(session).set(
        "shift.default",
        {
            "open": "09:00",
            "close": "13:30",
            "prep_eta": "13:45",
            "cancel_window_min": 30,
            "weekdays": [1, 2, 3, 4, 5],
        },
    )
    at(DURING)

    body = (await client.get(CURRENT)).json()

    assert (body["open_time"], body["close_time"], body["prep_eta"]) == ("09:00", "13:30", "13:45")
    assert body["cancel_deadline"] == "2026-09-24T16:00:00Z"  # 13:30 BA = 16:30Z, menos 30 min
    assert body["cancel_deadline_time"] == "13:00"  # y en hora local


async def test_the_shift_follows_the_configured_timezone(client, session, at):
    SettingsService(session).set("timezone", "America/Bogota")  # UTC-5
    at(DURING)

    body = (await client.get(CURRENT)).json()

    assert body["close_at"] == "2026-09-24T17:00:00Z"  # 12:00 en Bogotá


# ---------- dispara el cierre, una sola vez ----------


async def test_the_first_visit_after_closing_applies_the_closing_effects_once(
    client, session, at, monkeypatch
):
    calls: list[int] = []
    monkeypatch.setattr(shift_service, "_CLOSE_EFFECTS", [lambda ss, s: calls.append(s.id)])

    at(DURING)
    await client.get(CURRENT)
    assert calls == []  # todavía abierto: nada que cerrar

    at(AFTER_CLOSE)
    await client.get(CURRENT)
    await client.get(CURRENT)

    assert len(calls) == 1
    shift = session.scalars(select(Shift)).one()
    assert shift.closed_effects_applied_at == AFTER_CLOSE
    assert shift.status is ShiftStatus.CLOSED
