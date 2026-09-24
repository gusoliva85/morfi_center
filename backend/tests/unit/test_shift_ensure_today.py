from datetime import UTC, date, datetime

import pytest
from sqlalchemy import func, select

from app.core.enums import ServiceType, ShiftStatus
from app.models import Shift
from app.repositories.shift_repository import ShiftRepository
from app.services import shift_service
from app.services.settings_service import SettingsService
from app.services.shift_service import ShiftService

# 2026-09-24 es jueves (isoweekday 4); el 26 es sábado y el 27 domingo.
THURSDAY_NOON = datetime(2026, 9, 24, 15, 0, tzinfo=UTC)  # 12:00 en Buenos Aires
SATURDAY_NOON = datetime(2026, 9, 26, 15, 0, tzinfo=UTC)
SUNDAY_NOON = datetime(2026, 9, 27, 15, 0, tzinfo=UTC)


@pytest.fixture()
def service(session) -> ShiftService:
    return ShiftService(session)


def count_shifts(session) -> int:
    return session.scalar(select(func.count()).select_from(Shift))


def test_the_first_call_creates_todays_shift(service, session):
    shift = service.ensure_today_shift(THURSDAY_NOON)

    assert shift is not None
    assert shift.service_date == date(2026, 9, 24)
    assert shift.service_type is ServiceType.LUNCH
    assert shift.status is ShiftStatus.SCHEDULED
    assert count_shifts(session) == 1


def test_the_new_shift_copies_the_default_template(service):
    shift = service.ensure_today_shift(THURSDAY_NOON)

    assert (shift.open_time, shift.close_time) == ("08:00", "12:00")
    assert (shift.prep_eta, shift.dispatch_eta) == ("12:15", "12:30")
    assert shift.cancel_window_min == 20


def test_the_second_call_does_not_duplicate_it(service, session):
    """El caso del roadmap."""
    first = service.ensure_today_shift(THURSDAY_NOON)
    second = service.ensure_today_shift(THURSDAY_NOON)

    assert second.id == first.id
    assert count_shifts(session) == 1


def test_a_custom_template_is_used(service, session):
    SettingsService(session).set(
        "shift.default",
        {
            "open": "09:00",
            "close": "13:30",
            "cancel_window_min": 30,
            "weekdays": [1, 2, 3, 4, 5, 6, 7],
        },
    )

    shift = service.ensure_today_shift(THURSDAY_NOON)

    assert (shift.open_time, shift.close_time, shift.cancel_window_min) == ("09:00", "13:30", 30)
    assert shift.prep_eta is None


# ---------- días de operación ----------


@pytest.mark.parametrize("now", [SATURDAY_NOON, SUNDAY_NOON])
def test_no_shift_is_created_on_a_non_operating_day(service, session, now):
    assert service.ensure_today_shift(now) is None
    assert count_shifts(session) == 0


def test_a_day_added_to_the_weekdays_becomes_operating(service, session):
    SettingsService(session).set(
        "shift.default",
        {"open": "08:00", "close": "12:00", "cancel_window_min": 20, "weekdays": [6]},
    )

    assert service.ensure_today_shift(SATURDAY_NOON) is not None
    assert service.ensure_today_shift(THURSDAY_NOON) is None


def test_an_existing_shift_is_returned_even_on_a_non_operating_day(service, session):
    """Un admin pudo crear el turno del sábado a mano: no se lo esconde."""
    manual = ShiftRepository(session).create_from_default(
        date(2026, 9, 26), SettingsService(session).get_shift_default()
    )

    assert service.ensure_today_shift(SATURDAY_NOON).id == manual.id


# ---------- qué es "hoy" ----------


def test_today_is_the_local_date_not_the_utc_date(service):
    """23:00 en Buenos Aires ya es el día siguiente en UTC, pero el turno de
    hoy sigue siendo el del jueves 24."""
    late_thursday = datetime(2026, 9, 25, 2, 0, tzinfo=UTC)  # jueves 23:00 en BA

    assert service.ensure_today_shift(late_thursday).service_date == date(2026, 9, 24)


def test_midnight_local_starts_a_new_day(service):
    just_before = datetime(2026, 9, 24, 2, 59, 59, tzinfo=UTC)  # miércoles 23:59:59 en BA
    midnight = datetime(2026, 9, 24, 3, 0, 0, tzinfo=UTC)  # jueves 00:00 en BA

    assert service.ensure_today_shift(just_before).service_date == date(2026, 9, 23)
    assert service.ensure_today_shift(midnight).service_date == date(2026, 9, 24)


def test_today_follows_the_configured_timezone(service, session):
    SettingsService(session).set("timezone", "Pacific/Auckland")  # UTC+12
    thursday_evening_utc = datetime(2026, 9, 24, 20, 0, tzinfo=UTC)  # viernes 08:00 en Auckland

    assert service.ensure_today_shift(thursday_evening_utc).service_date == date(2026, 9, 25)


# ---------- lo ya creado no se toca ----------


def test_changing_the_template_does_not_alter_an_existing_shift(service, session):
    service.ensure_today_shift(THURSDAY_NOON)
    SettingsService(session).set(
        "shift.default",
        {"open": "10:00", "close": "14:00", "cancel_window_min": 5, "weekdays": [1, 2, 3, 4, 5]},
    )

    shift = service.ensure_today_shift(THURSDAY_NOON)

    assert (shift.open_time, shift.close_time) == ("08:00", "12:00")


def test_a_shift_is_created_even_after_its_closing_time(service):
    """Alguien entra a las 20:00 y todavía no había turno: se crea, y su estado
    (derivado de la hora) ya es CLOSED. No hay un horario de creación."""
    evening = datetime(2026, 9, 24, 23, 0, tzinfo=UTC)  # 20:00 en BA

    shift = service.ensure_today_shift(evening)

    assert service.current_status(shift, evening) is ShiftStatus.CLOSED


def test_without_a_now_it_uses_the_clock(service, monkeypatch):
    monkeypatch.setattr(shift_service, "now_utc", lambda: THURSDAY_NOON)

    assert service.ensure_today_shift().service_date == date(2026, 9, 24)


# ---------- carrera ----------


def commit_a_winner_and_go_stale(service, session, monkeypatch) -> tuple[Shift, list[date]]:
    """Otro request ya creó y guardó el turno de hoy, pero nuestra primera
    lectura quedó vieja y no lo ve (la segunda, sí). Devuelve el turno ganador
    y la lista de fechas leídas, para contar cuántas veces se leyó."""
    winner = ShiftRepository(session).create_from_default(
        date(2026, 9, 24), SettingsService(session).get_shift_default()
    )
    session.commit()  # el otro request ya terminó: su turno es visible para todos

    real_get_current = service.shifts.get_current
    reads: list[date] = []

    def stale_first_read(today, service_type=ServiceType.LUNCH):
        reads.append(today)
        return None if len(reads) == 1 else real_get_current(today, service_type)

    monkeypatch.setattr(service.shifts, "get_current", stale_first_read)
    return winner, reads


def test_a_simultaneous_creation_returns_the_shift_that_won(service, session, monkeypatch):
    """La base frena el segundo insert (UNIQUE) y se devuelve el ganador, sin
    error y sin duplicar."""
    winner, reads = commit_a_winner_and_go_stale(service, session, monkeypatch)

    shift = service.ensure_today_shift(THURSDAY_NOON)

    assert shift is not None
    assert shift.id == winner.id
    assert len(reads) == 2  # se volvió a leer tras el rollback
    assert count_shifts(session) == 1


def test_the_session_stays_usable_after_losing_the_race(service, session, monkeypatch):
    commit_a_winner_and_go_stale(service, session, monkeypatch)

    service.ensure_today_shift(THURSDAY_NOON)

    # Tras el rollback la sesión sigue andando: se puede seguir leyendo y escribiendo.
    SettingsService(session).set("stock.reservation_ttl_min", 25)
    assert SettingsService(session).get_stock_reservation_ttl_min() == 25
