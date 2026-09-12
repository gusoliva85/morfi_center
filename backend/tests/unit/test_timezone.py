"""Helpers de fecha/hora (`documentacion/02_Documento_Tecnico.md` §26).

Argentina opera en UTC-3 todo el año (sin horario de verano)."""

import datetime as dt

import pytest

from app.core import timezone as tz


def test_now_utc_is_aware_and_utc():
    now = tz.now_utc()
    assert now.tzinfo is dt.UTC
    assert abs((now - dt.datetime.now(dt.UTC)).total_seconds()) < 5


def test_resolve_shift_instant_buenos_aires():
    # 12:00 local en Buenos Aires (UTC-3) == 15:00 UTC
    instant = tz.resolve_shift_instant("2026-09-10", "12:00")
    assert instant == dt.datetime(2026, 9, 10, 15, 0, tzinfo=dt.UTC)
    assert instant.tzinfo is dt.UTC


def test_resolve_shift_instant_accepts_date_object():
    d = dt.date(2026, 9, 10)
    assert tz.resolve_shift_instant(d, "8:00") == dt.datetime(2026, 9, 10, 11, 0, tzinfo=dt.UTC)


def test_resolve_shift_instant_accepts_datetime_object():
    d = dt.datetime(2026, 9, 10, 23, 45)
    assert tz.resolve_shift_instant(d, "20:00") == dt.datetime(2026, 9, 10, 23, 0, tzinfo=dt.UTC)


def test_round_trip_local_wall_time_is_preserved():
    instant = tz.resolve_shift_instant("2026-01-15", "12:00")  # verano en AR, igual UTC-3
    local = tz.to_local(instant)
    assert (local.hour, local.minute) == (12, 0)
    assert local.utcoffset() == dt.timedelta(hours=-3)


def test_to_utc_from_naive_assumes_operation_tz():
    naive_noon = dt.datetime(2026, 9, 10, 12, 0)
    assert tz.to_utc(naive_noon) == dt.datetime(2026, 9, 10, 15, 0, tzinfo=dt.UTC)


def test_to_utc_from_aware_converts():
    aware = dt.datetime(2026, 9, 10, 12, 0, tzinfo=dt.timezone(dt.timedelta(hours=2)))
    assert tz.to_utc(aware) == dt.datetime(2026, 9, 10, 10, 0, tzinfo=dt.UTC)


def test_to_local_from_naive_assumes_utc():
    naive = dt.datetime(2026, 9, 10, 15, 0)
    local = tz.to_local(naive)
    assert (local.hour, local.minute) == (12, 0)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("00:00", dt.time(0, 0)),
        ("9:05", dt.time(9, 5)),
        ("23:59", dt.time(23, 59)),
        ("08:00", dt.time(8, 0)),
    ],
)
def test_parse_hhmm_valid(value, expected):
    assert tz.parse_hhmm(value) == expected


@pytest.mark.parametrize("value", ["25:00", "12:60", "noon", "12", "12:00:00", "", "1200"])
def test_parse_hhmm_invalid(value):
    with pytest.raises(ValueError):
        tz.parse_hhmm(value)


def test_isoformat_utc_ends_with_z():
    s = tz.isoformat_utc(dt.datetime(2026, 9, 10, 15, 0, tzinfo=dt.UTC))
    assert s == "2026-09-10T15:00:00Z"
    # también normaliza naive/local a UTC
    assert tz.isoformat_utc(dt.datetime(2026, 9, 10, 12, 0)).endswith("Z")
