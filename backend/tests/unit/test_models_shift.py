"""Modelo `Shift` (`03_Roadmap.md` T-2.2.1)."""

import datetime as dt

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.enums import ServiceType, ShiftStatus
from app.models.shift import Shift


def _make_shift(**overrides) -> Shift:
    defaults = {
        "service_date": "2026-09-15",
        "open_time": "08:00",
        "close_time": "12:00",
    }
    return Shift(**{**defaults, **overrides})


def test_create_and_read_a_shift_with_defaults(session):
    session.add(_make_shift())
    session.commit()

    shift = session.query(Shift).one()
    assert shift.service_date == "2026-09-15"
    assert shift.open_time == "08:00"
    assert shift.close_time == "12:00"
    assert shift.service_type == ServiceType.LUNCH
    assert shift.status == ShiftStatus.SCHEDULED
    assert shift.cancel_window_min == 20
    assert shift.prep_eta is None
    assert shift.dispatch_eta is None


def test_shift_has_utc_timestamps(session):
    session.add(_make_shift())
    session.commit()

    shift = session.query(Shift).one()
    assert shift.created_at.tzinfo is dt.UTC
    assert shift.updated_at.tzinfo is dt.UTC


def test_same_date_and_service_type_cannot_repeat(session):
    session.add(_make_shift())
    session.commit()

    session.add(_make_shift())
    with pytest.raises(IntegrityError):
        session.commit()


def test_same_date_different_service_type_is_allowed(session):
    session.add(_make_shift(service_type=ServiceType.LUNCH))
    session.add(_make_shift(service_type=ServiceType.DINNER))
    session.commit()

    assert session.query(Shift).count() == 2
