from datetime import UTC, date, datetime

from app.core.timezone import now_utc, resolve_shift_instant, to_local


def test_resolve_shift_instant_buenos_aires_is_utc_minus_3():
    # Buenos Aires no tiene horario de verano desde 2009: UTC-3 todo el año.
    result = resolve_shift_instant("2026-09-10", "12:00")
    assert result == datetime(2026, 9, 10, 15, 0, tzinfo=UTC)


def test_resolve_shift_instant_accepts_date_object():
    result = resolve_shift_instant(date(2026, 12, 25), "08:30")
    assert result == datetime(2026, 12, 25, 11, 30, tzinfo=UTC)


def test_now_utc_is_timezone_aware_utc():
    result = now_utc()
    assert result.tzinfo is not None
    assert result.utcoffset().total_seconds() == 0


def test_to_local_converts_utc_to_buenos_aires():
    dt_utc = datetime(2026, 9, 10, 15, 0, tzinfo=UTC)
    local = to_local(dt_utc)
    assert local.hour == 12
    assert local.utcoffset().total_seconds() == -3 * 3600


def test_to_local_treats_naive_datetime_as_utc():
    naive = datetime(2026, 9, 10, 15, 0)
    local = to_local(naive)
    assert local.hour == 12
