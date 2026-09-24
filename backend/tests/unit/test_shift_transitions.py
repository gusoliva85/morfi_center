import json
from datetime import UTC, date, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm.attributes import set_committed_value

from app.core.enums import Role, ShiftStatus
from app.core.errors import ForbiddenError, InvalidTransitionError
from app.core.security import hash_password
from app.models import AuditLog, Shift, User
from app.repositories.shift_repository import ShiftRepository
from app.repositories.user_repository import UserRepository
from app.services import shift_service
from app.services.settings_service import SettingsService
from app.services.shift_service import ShiftService

# Turno del jueves 24/09/2026, 08:00-12:00 en Buenos Aires (11:00Z - 15:00Z).
DURING = datetime(2026, 9, 24, 13, 0, tzinfo=UTC)
BEFORE = datetime(2026, 9, 24, 10, 0, tzinfo=UTC)
AT_CLOSE = datetime(2026, 9, 24, 15, 0, tzinfo=UTC)
AFTER = datetime(2026, 9, 24, 16, 30, tzinfo=UTC)
LATER = datetime(2026, 9, 24, 18, 0, tzinfo=UTC)


@pytest.fixture()
def service(session) -> ShiftService:
    return ShiftService(session)


@pytest.fixture()
def shift(session) -> Shift:
    created = ShiftRepository(session).create_from_default(
        date(2026, 9, 24), SettingsService(session).get_shift_default()
    )
    session.commit()  # como si viniera de un request anterior
    return created


@pytest.fixture()
def effects(monkeypatch) -> list[int]:
    """Un efecto de cierre espía: anota el id del turno cada vez que corre.
    Lista de efectos aislada por test para no contaminar a los demás."""
    calls: list[int] = []
    monkeypatch.setattr(shift_service, "_CLOSE_EFFECTS", [lambda session, s: calls.append(s.id)])
    return calls


@pytest.fixture()
def make_user(session):
    def make(role: Role) -> User:
        user = UserRepository(session).create(
            first_name="T",
            last_name=role.value.title(),
            email=f"{role.value.lower()}@example.com",
            password_hash=hash_password("secreta123"),
            role=role,
        )
        session.flush()
        return user

    return make


def audit_rows(session) -> list[AuditLog]:
    return list(session.scalars(select(AuditLog).where(AuditLog.entity_type == "shift")))


# ---------- el estado se deriva solo, sin llamar nada ----------


def test_the_status_changes_with_the_clock_without_calling_anything(service, shift):
    """No hay un "abrir" ni un "cerrar" que correr: solo pasa el tiempo."""
    assert service.current_status(shift, BEFORE) is ShiftStatus.SCHEDULED
    assert service.current_status(shift, DURING) is ShiftStatus.OPEN
    assert service.current_status(shift, AFTER) is ShiftStatus.CLOSED
    assert shift.status is ShiftStatus.SCHEDULED  # y nada se guardó


# ---------- on_shift_closed ----------


def test_nothing_happens_before_the_shift_closes(service, shift, effects):
    assert service.on_shift_closed(shift, BEFORE) is False
    assert service.on_shift_closed(shift, DURING) is False

    assert shift.closed_effects_applied_at is None
    assert effects == []


def test_the_closing_effects_run_when_the_closing_is_first_detected(service, shift, effects):
    applied = service.on_shift_closed(shift, AFTER)

    assert applied is True
    assert effects == [shift.id]
    assert shift.closed_effects_applied_at == AFTER


def test_the_exact_closing_instant_already_counts_as_closed(service, shift, effects):
    assert service.on_shift_closed(shift, AT_CLOSE) is True


def test_the_effects_apply_only_once_across_two_requests_in_a_row(service, shift, effects):
    """El caso del roadmap."""
    first = service.on_shift_closed(shift, AFTER)
    second = service.on_shift_closed(shift, LATER)

    assert (first, second) == (True, False)
    assert effects == [shift.id]  # una sola vez
    assert shift.closed_effects_applied_at == AFTER  # la marca no se corre


def test_a_request_with_a_stale_view_of_the_shift_does_not_repeat_the_effects(
    service, session, shift, effects
):
    """Dos requests simultáneos: el segundo cargó el turno *antes* de que el
    primero lo marcara, así que lo ve sin marca. La base decide: el UPDATE
    condicional no encuentra fila para modificar y no repite nada."""
    service.on_shift_closed(shift, AFTER)
    session.commit()
    set_committed_value(shift, "closed_effects_applied_at", None)  # vista vieja

    repeated = service.on_shift_closed(shift, LATER)

    assert repeated is False
    assert effects == [shift.id]
    assert shift.closed_effects_applied_at == AFTER  # se refrescó con lo real


def test_closing_is_also_saved_as_the_stored_status(service, shift, effects):
    service.on_shift_closed(shift, AFTER)

    assert shift.status is ShiftStatus.CLOSED


def test_the_mark_is_stored_as_a_utc_datetime(service, session, shift, effects):
    service.on_shift_closed(shift, AFTER)
    session.commit()
    session.expire_all()

    stored = session.get(Shift, shift.id).closed_effects_applied_at
    assert stored == AFTER
    assert stored.tzinfo is not None


def test_a_failing_effect_leaves_the_shift_unmarked_so_the_next_request_retries(
    service, session, shift, monkeypatch
):
    """La marca y los efectos van en la misma transacción: si un efecto falla,
    el request se deshace entero y no queda un turno "cerrado a medias"."""

    def broken(session, s):
        raise RuntimeError("falló el efecto")

    monkeypatch.setattr(shift_service, "_CLOSE_EFFECTS", [broken])
    with pytest.raises(RuntimeError):
        service.on_shift_closed(shift, AFTER)
    session.rollback()  # lo que hace get_session ante una excepción

    session.refresh(shift)
    assert shift.closed_effects_applied_at is None

    ran: list[int] = []
    monkeypatch.setattr(shift_service, "_CLOSE_EFFECTS", [lambda ss, s: ran.append(s.id)])
    assert service.on_shift_closed(shift, LATER) is True
    assert ran == [shift.id]


def test_with_no_registered_effects_it_still_marks_the_closing(service, shift, monkeypatch):
    monkeypatch.setattr(shift_service, "_CLOSE_EFFECTS", [])

    assert service.on_shift_closed(shift, AFTER) is True
    assert shift.closed_effects_applied_at == AFTER


def test_without_a_now_it_uses_the_clock(service, shift, effects, monkeypatch):
    monkeypatch.setattr(shift_service, "now_utc", lambda: AFTER)

    assert service.on_shift_closed(shift) is True


def test_register_close_effect_adds_to_the_registry(monkeypatch):
    monkeypatch.setattr(shift_service, "_CLOSE_EFFECTS", [])

    def effect(session, s):
        return None

    shift_service.register_close_effect(effect)

    assert shift_service._CLOSE_EFFECTS == [effect]


# ---------- to_production ----------


def test_an_admin_moves_a_closed_shift_to_production(service, shift, make_user, effects):
    admin = make_user(Role.ADMIN)

    result = service.to_production(shift, admin, AFTER)

    assert result.status is ShiftStatus.IN_PRODUCTION


def test_to_production_guarantees_the_closing_effects_were_applied(
    service, shift, make_user, effects
):
    """Aunque nadie hubiera consultado el turno desde que cerró."""
    service.to_production(shift, make_user(Role.ADMIN), AFTER)

    assert effects == [shift.id]
    assert shift.closed_effects_applied_at == AFTER


def test_to_production_does_not_repeat_effects_already_applied(service, shift, make_user, effects):
    service.on_shift_closed(shift, AFTER)

    service.to_production(shift, make_user(Role.ADMIN), LATER)

    assert effects == [shift.id]  # no se repitió


@pytest.mark.parametrize("role", [Role.CUSTOMER, Role.DELIVERY])
def test_only_an_admin_can_move_a_shift_to_production(service, shift, make_user, effects, role):
    with pytest.raises(ForbiddenError):
        service.to_production(shift, make_user(role), AFTER)

    assert shift.status is ShiftStatus.SCHEDULED
    assert effects == []  # y tampoco se cerró nada por el camino


@pytest.mark.parametrize("now", [BEFORE, DURING])
def test_a_shift_still_taking_orders_cannot_go_to_production(service, shift, make_user, now):
    with pytest.raises(InvalidTransitionError) as exc_info:
        service.to_production(shift, make_user(Role.ADMIN), now)

    assert exc_info.value.status_code == 409
    assert shift.status is ShiftStatus.SCHEDULED


def test_it_cannot_go_to_production_twice(service, shift, make_user, effects):
    admin = make_user(Role.ADMIN)
    service.to_production(shift, admin, AFTER)

    with pytest.raises(InvalidTransitionError):
        service.to_production(shift, admin, LATER)


@pytest.mark.parametrize("status", [ShiftStatus.DISPATCHING, ShiftStatus.FINISHED])
def test_a_shift_further_along_cannot_go_back_to_production(service, shift, make_user, status):
    ShiftRepository(service.session).set_status(shift, status)

    with pytest.raises(InvalidTransitionError):
        service.to_production(shift, make_user(Role.ADMIN), AFTER)

    assert shift.status is status


def test_going_to_production_leaves_an_audit_trail(service, session, shift, make_user, effects):
    admin = make_user(Role.ADMIN)

    service.to_production(shift, admin, AFTER, ip="203.0.113.7")

    (entry,) = audit_rows(session)
    assert entry.action == "shift.to_production"
    assert entry.entity_id == str(shift.id)
    assert entry.actor_id == admin.id
    assert entry.ip == "203.0.113.7"
    assert json.loads(entry.data) == {
        "before": {"status": "SCHEDULED"},
        "after": {"status": "IN_PRODUCTION"},
    }


def test_a_rejected_attempt_leaves_no_audit_trail(service, session, shift, make_user):
    with pytest.raises(InvalidTransitionError):
        service.to_production(shift, make_user(Role.ADMIN), DURING)

    assert audit_rows(session) == []


def test_ordering_stays_closed_after_going_to_production(service, shift, make_user, effects):
    service.to_production(shift, make_user(Role.ADMIN), AFTER)

    assert service.is_ordering_open(shift, DURING) is False  # aunque el reloj dijera abierto
