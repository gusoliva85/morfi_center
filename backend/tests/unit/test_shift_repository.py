"""`ShiftRepository` (`03_Roadmap.md` T-2.2.1)."""

from app.core.enums import ServiceType, ShiftStatus
from app.repositories.shift_repository import ShiftRepository


def _repo(session) -> ShiftRepository:
    return ShiftRepository(session)


# ── create_from_default + get_by_date_type: ida y vuelta ──
def test_create_and_retrieve_a_shift_by_date_and_type(session):
    repo = _repo(session)
    created = repo.create_from_default(
        service_date="2026-09-15",
        open_time="08:00",
        close_time="12:00",
        prep_eta="12:15",
        dispatch_eta="12:30",
        cancel_window_min=20,
    )

    found = repo.get_by_date_type("2026-09-15", ServiceType.LUNCH)
    assert found is not None
    assert found.id == created.id
    assert found.open_time == "08:00"
    assert found.close_time == "12:00"
    assert found.prep_eta == "12:15"
    assert found.dispatch_eta == "12:30"


def test_create_from_default_uses_lunch_and_cancel_window_20_by_default(session):
    shift = _repo(session).create_from_default(
        service_date="2026-09-15", open_time="08:00", close_time="12:00"
    )
    assert shift.service_type == ServiceType.LUNCH
    assert shift.cancel_window_min == 20
    assert shift.status == ShiftStatus.SCHEDULED


def test_get_by_date_type_returns_none_when_missing(session):
    assert _repo(session).get_by_date_type("2099-01-01") is None


def test_get_by_date_type_distinguishes_service_type(session):
    repo = _repo(session)
    repo.create_from_default(
        service_date="2026-09-15",
        open_time="08:00",
        close_time="12:00",
        service_type=ServiceType.LUNCH,
    )
    assert repo.get_by_date_type("2026-09-15", ServiceType.DINNER) is None


# ── get_current ─────────────────────────────────────────────
def test_get_current_defaults_to_lunch(session):
    repo = _repo(session)
    created = repo.create_from_default(
        service_date="2026-09-15", open_time="08:00", close_time="12:00"
    )
    found = repo.get_current("2026-09-15")
    assert found is not None
    assert found.id == created.id


def test_get_current_with_explicit_service_type(session):
    repo = _repo(session)
    repo.create_from_default(
        service_date="2026-09-15",
        open_time="20:00",
        close_time="23:00",
        service_type=ServiceType.DINNER,
    )
    assert repo.get_current("2026-09-15", ServiceType.LUNCH) is None
    assert repo.get_current("2026-09-15", ServiceType.DINNER) is not None


# ── set_status ──────────────────────────────────────────────
def test_set_status_persists(session):
    repo = _repo(session)
    shift = repo.create_from_default(
        service_date="2026-09-15", open_time="08:00", close_time="12:00"
    )
    repo.set_status(shift, ShiftStatus.OPEN)

    reloaded = repo.get_by_date_type("2026-09-15", ServiceType.LUNCH)
    assert reloaded.status == ShiftStatus.OPEN
