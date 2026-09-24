from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.enums import ServiceType, ShiftStatus
from app.models import Shift
from app.repositories.shift_repository import ShiftRepository
from app.schemas.settings import ShiftDefault

TODAY = date(2026, 9, 24)

TEMPLATE = ShiftDefault(
    open="08:00",
    close="12:00",
    prep_eta="12:15",
    dispatch_eta="12:30",
    cancel_window_min=20,
    weekdays=[1, 2, 3, 4, 5],
)


@pytest.fixture()
def repo(session) -> ShiftRepository:
    return ShiftRepository(session)


def test_a_created_shift_is_read_back_by_date_and_type(repo):
    """El caso del roadmap."""
    created = repo.create_from_default(TODAY, TEMPLATE)

    found = repo.get_by_date_type(TODAY, ServiceType.LUNCH)

    assert found is not None
    assert found.id == created.id
    assert found.service_date == TODAY


def test_the_shift_copies_the_template(repo):
    shift = repo.create_from_default(TODAY, TEMPLATE)

    assert (shift.open_time, shift.close_time) == ("08:00", "12:00")
    assert (shift.prep_eta, shift.dispatch_eta) == ("12:15", "12:30")
    assert shift.cancel_window_min == 20


def test_the_optional_etas_may_be_missing(repo):
    template = ShiftDefault(open="08:00", close="12:00", cancel_window_min=20, weekdays=[1])

    shift = repo.create_from_default(TODAY, template)

    assert (shift.prep_eta, shift.dispatch_eta) == (None, None)


def test_a_new_shift_defaults_to_lunch_and_scheduled(repo):
    shift = repo.create_from_default(TODAY, TEMPLATE)

    assert shift.service_type is ServiceType.LUNCH
    assert shift.status is ShiftStatus.SCHEDULED
    assert shift.created_at and shift.updated_at


def test_changing_the_template_later_does_not_alter_an_existing_shift(repo):
    """Se copia, no se referencia: el turno de hoy no cambia porque el admin
    edite la plantilla a media mañana."""
    shift = repo.create_from_default(TODAY, TEMPLATE)

    later_template = TEMPLATE.model_copy(update={"close": "13:00"})
    repo.create_from_default(date(2026, 9, 25), later_template)

    assert repo.get_by_date_type(TODAY).close_time == "12:00"
    assert shift.close_time == "12:00"


def test_get_by_date_type_returns_none_when_there_is_no_shift(repo):
    assert repo.get_by_date_type(TODAY) is None


def test_the_lookup_distinguishes_date_and_type(repo):
    repo.create_from_default(TODAY, TEMPLATE, ServiceType.LUNCH)
    repo.create_from_default(TODAY, TEMPLATE, ServiceType.DINNER)

    assert repo.get_by_date_type(TODAY, ServiceType.DINNER).service_type is ServiceType.DINNER
    assert repo.get_by_date_type(TODAY, ServiceType.BREAKFAST) is None
    assert repo.get_by_date_type(date(2026, 9, 25), ServiceType.LUNCH) is None


def test_get_current_is_the_shift_of_today(repo):
    today_shift = repo.create_from_default(TODAY, TEMPLATE)
    repo.create_from_default(date(2026, 9, 25), TEMPLATE)

    assert repo.get_current(TODAY).id == today_shift.id
    assert repo.get_current(date(2026, 9, 30)) is None


def test_two_shifts_of_the_same_date_and_type_are_rejected(repo):
    """Lo garantiza la base (UNIQUE), no solo el código: dos requests
    simultáneos no pueden crear dos turnos para el mismo día."""
    repo.create_from_default(TODAY, TEMPLATE)

    with pytest.raises(IntegrityError):
        repo.create_from_default(TODAY, TEMPLATE)


def test_set_status_persists_the_new_status(repo):
    shift = repo.create_from_default(TODAY, TEMPLATE)

    repo.set_status(shift, ShiftStatus.IN_PRODUCTION)

    repo.session.expire_all()
    assert repo.get_by_date_type(TODAY).status is ShiftStatus.IN_PRODUCTION


def test_set_status_touches_updated_at(repo):
    shift = repo.create_from_default(TODAY, TEMPLATE)
    before = shift.updated_at

    repo.set_status(shift, ShiftStatus.FINISHED)

    assert shift.updated_at >= before


def test_service_date_is_stored_as_an_iso_date(repo):
    """Como pide §6.4: 'YYYY-MM-DD', legible por cualquier otra herramienta."""
    repo.create_from_default(TODAY, TEMPLATE)

    raw = repo.session.execute(text("SELECT service_date FROM shifts")).scalar_one()
    assert raw == "2026-09-24"


def test_the_database_rejects_a_negative_cancel_window(session):
    session.add(
        Shift(
            service_date=TODAY,
            open_time="08:00",
            close_time="12:00",
            cancel_window_min=-1,
        )
    )

    with pytest.raises(IntegrityError):
        session.flush()


def test_the_database_rejects_an_unknown_status(session):
    """Con SQL directo: así se prueba el CHECK de la base y no la validación
    previa de SQLAlchemy."""
    with pytest.raises(IntegrityError):
        session.execute(
            text(
                "INSERT INTO shifts (service_date, service_type, open_time, close_time, "
                "cancel_window_min, status, created_at, updated_at) VALUES "
                "('2026-09-24', 'LUNCH', '08:00', '12:00', 20, 'OTRO', "
                "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            )
        )
