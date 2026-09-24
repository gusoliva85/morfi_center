from datetime import UTC, date, datetime, timedelta, timezone

import pytest

from app.core.config import settings
from app.core.enums import ShiftStatus
from app.models import Shift
from app.services import shift_service
from app.services.settings_service import SettingsService
from app.services.shift_service import (
    ShiftService,
    current_status,
    is_ordering_open,
    resolve_window,
)

BA = "America/Argentina/Buenos_Aires"  # UTC-3 todo el año
DAY = date(2026, 9, 24)


def make_shift(
    *,
    service_date: date = DAY,
    open_time: str = "08:00",
    close_time: str = "12:00",
    cancel_window_min: int = 20,
    status: ShiftStatus = ShiftStatus.SCHEDULED,
) -> Shift:
    """Un turno en memoria: estas cuentas no necesitan la base."""
    return Shift(
        service_date=service_date,
        open_time=open_time,
        close_time=close_time,
        cancel_window_min=cancel_window_min,
        status=status,
    )


def utc(hour: int, minute: int = 0, second: int = 0, *, day: int = 24) -> datetime:
    return datetime(2026, 9, day, hour, minute, second, tzinfo=UTC)


# ---------- resolve_window ----------


def test_the_window_converts_local_wall_times_to_utc():
    window = resolve_window(make_shift(), BA)

    assert window.open_at == utc(11, 0)  # 08:00 en Buenos Aires
    assert window.close_at == utc(15, 0)  # 12:00
    assert window.cancel_deadline == utc(14, 40)  # cierre menos 20 minutos


def test_the_window_is_always_utc():
    window = resolve_window(make_shift(), BA)

    for instant in (window.open_at, window.close_at, window.cancel_deadline):
        assert instant.utcoffset() == timedelta(0)


def test_a_zero_cancel_window_puts_the_deadline_at_closing():
    window = resolve_window(make_shift(cancel_window_min=0), BA)

    assert window.cancel_deadline == window.close_at


def test_the_window_follows_the_timezone_it_is_given():
    bogota = resolve_window(make_shift(), "America/Bogota")  # UTC-5

    assert bogota.close_at == utc(17, 0)


@pytest.mark.parametrize(
    ("service_date", "expected_utc_hour"),
    [(date(2026, 1, 15), 11), (date(2026, 7, 1), 10)],  # invierno UTC+1, verano UTC+2
)
def test_the_window_honours_daylight_saving_time(service_date, expected_utc_hour):
    """Con zonas que cambian la hora, la misma hora de pared cae en instantes
    distintos según la fecha del turno."""
    window = resolve_window(make_shift(service_date=service_date), "Europe/Madrid")

    assert window.close_at.hour == expected_utc_hour


def test_the_window_uses_the_shifts_own_date():
    tomorrow = resolve_window(make_shift(service_date=DAY + timedelta(days=1)), BA)

    assert tomorrow.close_at == utc(15, 0, day=25)


# ---------- current_status ----------


@pytest.mark.parametrize(
    ("now", "expected"),
    [
        (utc(10, 59, 59), ShiftStatus.SCHEDULED),  # un segundo antes de abrir
        (utc(11, 0, 0), ShiftStatus.OPEN),  # abre en punto (inclusive)
        (utc(13, 0), ShiftStatus.OPEN),
        (utc(14, 59, 59), ShiftStatus.OPEN),  # un segundo antes de cerrar
        (utc(15, 0, 0), ShiftStatus.CLOSED),  # cierra en punto (exclusive)
        (utc(20, 0), ShiftStatus.CLOSED),
        (utc(15, 0, day=25), ShiftStatus.CLOSED),  # al día siguiente
        (utc(15, 0, day=23), ShiftStatus.SCHEDULED),  # el día anterior
    ],
)
def test_status_before_during_and_after_the_window(now, expected):
    assert current_status(make_shift(), now, BA) is expected


def test_the_same_now_always_gives_the_same_status():
    """Función pura (§9.9): nada depende de cuántas veces se pregunte."""
    shift = make_shift()

    assert {current_status(shift, utc(13), BA) for _ in range(5)} == {ShiftStatus.OPEN}


def test_status_accepts_a_now_expressed_in_another_timezone():
    local_09 = datetime(2026, 9, 24, 9, 0, tzinfo=timezone(timedelta(hours=-3)))  # = 12:00Z

    assert current_status(make_shift(), local_09, BA) is ShiftStatus.OPEN


def test_status_is_derived_from_the_clock_not_from_the_stored_status():
    """Un turno guardado como SCHEDULED sigue siendo derivable como CLOSED."""
    shift = make_shift(status=ShiftStatus.SCHEDULED)

    assert current_status(shift, utc(20), BA) is ShiftStatus.CLOSED


# ---------- is_ordering_open ----------


def test_ordering_is_open_only_inside_the_window():
    shift = make_shift()

    assert is_ordering_open(shift, utc(10, 59), BA) is False
    assert is_ordering_open(shift, utc(13), BA) is True
    assert is_ordering_open(shift, utc(15), BA) is False


@pytest.mark.parametrize(
    "status", [ShiftStatus.IN_PRODUCTION, ShiftStatus.DISPATCHING, ShiftStatus.FINISHED]
)
def test_ordering_is_closed_once_the_admin_moved_past_closing(status):
    """Aunque el reloj diga que sigue abierto (el admin adelantó la producción)."""
    shift = make_shift(status=status)

    assert current_status(shift, utc(13), BA) is ShiftStatus.OPEN  # el reloj sí lo diría
    assert is_ordering_open(shift, utc(13), BA) is False


@pytest.mark.parametrize("status", [ShiftStatus.SCHEDULED, ShiftStatus.OPEN, ShiftStatus.CLOSED])
def test_the_stored_time_based_statuses_do_not_block_ordering(status):
    """SCHEDULED/OPEN/CLOSED guardados no cuentan: manda la hora."""
    assert is_ordering_open(make_shift(status=status), utc(13), BA) is True


# ---------- ShiftService (zona horaria desde la configuración) ----------


@pytest.fixture()
def service(session) -> ShiftService:
    return ShiftService(session)


def test_the_service_uses_the_configured_timezone_by_default(service):
    assert service.settings.get_timezone() == settings.app_timezone
    assert service.resolve_window(make_shift()).close_at == utc(15, 0)


def test_the_timezone_setting_rules_over_the_environment(service, session):
    """Cuando el admin cambia la zona, los turnos se resuelven con la nueva."""
    SettingsService(session).set("timezone", "America/Bogota")

    assert service.resolve_window(make_shift()).close_at == utc(17, 0)


def test_the_service_answers_status_for_a_given_now(service):
    shift = make_shift()

    assert service.current_status(shift, utc(10, 0)) is ShiftStatus.SCHEDULED
    assert service.current_status(shift, utc(13, 0)) is ShiftStatus.OPEN
    assert service.is_ordering_open(shift, utc(13, 0)) is True


def test_without_a_now_the_service_uses_the_clock(service, monkeypatch):
    shift = make_shift()

    monkeypatch.setattr(shift_service, "now_utc", lambda: utc(13, 0))
    assert service.current_status(shift) is ShiftStatus.OPEN
    assert service.is_ordering_open(shift) is True

    monkeypatch.setattr(shift_service, "now_utc", lambda: utc(16, 0))
    assert service.current_status(shift) is ShiftStatus.CLOSED
