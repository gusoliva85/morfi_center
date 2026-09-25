import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from pydantic import ValidationError
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.enums import Role, ShiftStatus
from app.core.errors import (
    DomainValidationError,
    ForbiddenError,
    InvalidTransitionError,
    NotFoundError,
)
from app.core.timezone import now_utc, resolve_shift_instant, to_local
from app.models import AuditLog, Shift, User
from app.repositories.shift_repository import ShiftRepository
from app.schemas.settings import ShiftSchedule
from app.services.settings_service import SettingsService, fields_from_validation_error

NO_SERVICE = "NO_SERVICE"  # hoy no es día de operación: no hay turno

SHIFT_NOT_FOUND = "No existe ese turno."
INVALID_SCHEDULE = "Los horarios del turno no son válidos."
LOCKED_AFTER_CLOSING = (
    "El turno ya cerró y sus efectos ya se aplicaron: no se pueden cambiar la apertura, "
    "el cierre ni la ventana de cancelación (sí las horas estimadas)."
)
NOT_TODAYS_SHIFT = "Solo se puede abrir o cerrar el turno de hoy."
ALREADY_OPEN = "El turno ya está abierto."
ALREADY_CLOSED = "El turno ya está cerrado."
NOT_OPEN_YET = "El turno todavía no abrió: para cambiar el horario usá la edición del turno."
CLOSED_CANNOT_REOPEN = (
    "El turno ya cerró: para reabrirlo hay que ampliar la hora de cierre desde la edición "
    "del turno (mientras sus efectos de cierre no se hayan aplicado)."
)
CLOSE_TOO_SOON = "El turno acaba de abrir: esperá al menos un minuto para cerrarlo."

# Qué campos de la API se llaman distinto en el molde de horarios (`open`/`close`).
_API_FIELD = {"open": "open_time", "close": "close_time"}
_TO_SCHEDULE_FIELD = {"open_time": "open", "close_time": "close"}
_LOCKED_FIELDS = ("open_time", "close_time", "cancel_window_min")

ONLY_ADMIN = "Solo un administrador puede pasar el turno a producción."
ONLY_ADMIN_EDIT = "Solo un administrador puede modificar los turnos."
NOT_CLOSED_YET = "El turno todavía no cerró: hay que esperar a que terminen los pedidos."
ALREADY_IN_PRODUCTION = "El turno ya está en producción (o más avanzado)."

# Estados que solo existen porque un admin los puso a mano: una vez ahí, el
# turno ya no acepta pedidos aunque el reloj diga otra cosa.
_PAST_CLOSING = (ShiftStatus.IN_PRODUCTION, ShiftStatus.DISPATCHING, ShiftStatus.FINISHED)

# Efectos de una sola vez del cierre del turno (`on_shift_closed`). Hoy no hay
# ninguno: cada fase que necesite uno lo registra acá con `register_close_effect`
# (Fase 4: congelar `product_stock` del turno; Fase 11: marcar como críticos los
# pedidos sin validar). Reciben la sesión y el turno, y corren **dentro de la
# misma transacción** que la marca de "ya aplicado": si uno falla, se deshace
# todo y el próximo request lo reintenta.
CloseEffect = Callable[[Session, Shift], None]
_CLOSE_EFFECTS: list[CloseEffect] = []


def register_close_effect(effect: CloseEffect) -> None:
    _CLOSE_EFFECTS.append(effect)


@dataclass(frozen=True)
class ShiftDetail:
    """Un turno más lo que se deriva de la hora, para el panel de admin."""

    shift: Shift
    window: "ShiftWindow"
    status: ShiftStatus  # ciclo de vida completo (`effective_status`)
    ordering_open: bool


@dataclass(frozen=True)
class ShiftSnapshot:
    """El turno de hoy tal como se ve en este instante. Sin turno (`shift` es
    `None`), `status` es `NO_SERVICE` y no hay ventana ni cuenta regresiva."""

    now: datetime
    status: str  # SCHEDULED | OPEN | CLOSED | NO_SERVICE
    shift: Shift | None
    window: "ShiftWindow | None"
    ordering_open: bool
    seconds_to_close: int | None
    cancel_deadline_time: str | None = None  # HH:MM local, para mostrar


@dataclass(frozen=True)
class ShiftWindow:
    """Los tres instantes que gobiernan un turno, todos en UTC."""

    open_at: datetime
    close_at: datetime
    cancel_deadline: datetime  # `close_at` menos la ventana de cancelación


def resolve_window(shift: Shift, tz: str) -> ShiftWindow:
    """Convierte los horarios de pared del turno (`'08:00'`) en instantes UTC,
    según su `service_date` y la zona `tz`. Función pura: no toca la base."""
    close_at = resolve_shift_instant(shift.service_date, shift.close_time, tz)
    return ShiftWindow(
        open_at=resolve_shift_instant(shift.service_date, shift.open_time, tz),
        close_at=close_at,
        cancel_deadline=close_at - timedelta(minutes=shift.cancel_window_min),
    )


def current_status(shift: Shift, now: datetime, tz: str) -> ShiftStatus:
    """`SCHEDULED`, `OPEN` o `CLOSED` según la hora. **Nunca se guarda ni lo
    cambia un proceso de fondo** (§9.9): con el mismo `now` da siempre lo mismo.

    Abre en `open_at` (inclusive) y cierra en `close_at` (exclusive): a las
    12:00 en punto ya está cerrado, no queda un instante de más para pedir.
    """
    window = resolve_window(shift, tz)
    if now < window.open_at:
        return ShiftStatus.SCHEDULED
    if now < window.close_at:
        return ShiftStatus.OPEN
    return ShiftStatus.CLOSED


def effective_status(shift: Shift, now: datetime, tz: str) -> ShiftStatus:
    """El estado del ciclo de vida completo: si el admin ya avanzó el turno
    (`IN_PRODUCTION`, ...) es ese; si no, el que dice el reloj."""
    if shift.status in _PAST_CLOSING:
        return shift.status
    return current_status(shift, now, tz)


def is_ordering_open(shift: Shift, now: datetime, tz: str) -> bool:
    """¿Se puede hacer un pedido ahora? Además del reloj, el admin puede haber
    pasado el turno a producción (o más allá) antes de la hora de cierre: en ese
    caso ya no acepta pedidos."""
    if shift.status in _PAST_CLOSING:
        return False
    return current_status(shift, now, tz) is ShiftStatus.OPEN


class ShiftService:
    """Las mismas cuentas de arriba, con la zona horaria tomada de la
    configuración (`timezone`, T-2.1.2) y `now` opcional (por defecto, ahora)."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.settings = SettingsService(session)
        self.shifts = ShiftRepository(session)

    def resolve_window(self, shift: Shift) -> ShiftWindow:
        return resolve_window(shift, self.settings.get_timezone())

    def current_status(self, shift: Shift, now: datetime | None = None) -> ShiftStatus:
        return current_status(shift, now or now_utc(), self.settings.get_timezone())

    def is_ordering_open(self, shift: Shift, now: datetime | None = None) -> bool:
        return is_ordering_open(shift, now or now_utc(), self.settings.get_timezone())

    def ensure_today_shift(self, now: datetime | None = None) -> Shift | None:
        """El turno de hoy, creándolo con la plantilla `shift.default` si todavía
        no existe. `None` si hoy no es un día de operación (`weekdays`).

        No hay un proceso que lo cree de madrugada (§9.9): lo dispara el primer
        flujo que necesita "el turno de hoy" (`GET /shift/current`, crear un
        pedido, abrir el panel admin). "Hoy" es la fecha **local** en la zona
        configurada, no la de UTC: a las 23:00 de Buenos Aires ya es el día
        siguiente en UTC, pero el turno sigue siendo el de hoy.

        Un turno que ya existe se devuelve tal cual aunque hoy no sea día de
        operación (un admin pudo crearlo a mano) y aunque la plantilla haya
        cambiado desde entonces: no se toca lo ya creado.

        Llamarlo **al principio** del flujo: si dos requests lo crean a la vez,
        la base frena al segundo (`UNIQUE`) y acá se hace `rollback` de la
        transacción completa —igual que en el registro de usuarios— para leer el
        turno que ganó. Lo pendiente sin guardar de esa transacción se pierde.
        """
        tz = self.settings.get_timezone()
        today = to_local(now or now_utc(), tz).date()

        shift = self.shifts.get_current(today)
        if shift is not None:
            return shift

        template = self.settings.get_shift_default()
        if today.isoweekday() not in template.weekdays:
            return None

        try:
            return self.shifts.create_from_default(today, template)
        except IntegrityError:
            self.session.rollback()
            return self.shifts.get_current(today)

    def on_shift_closed(self, shift: Shift, now: datetime | None = None) -> bool:
        """Aplica **una sola vez** los efectos del cierre (§9.9). Devuelve
        `True` si esta llamada los aplicó, `False` si el turno todavía no cerró
        o ya estaban aplicados.

        No es un job: lo llama cualquier request que consulte el turno (de un
        cliente o del admin) y solo hace algo la primera vez que ve el cierre.
        Es seguro llamarlo siempre.

        Aunque dos requests lo detecten a la vez, uno solo lo aplica: se
        "reclama" con un `UPDATE ... WHERE closed_effects_applied_at IS NULL`
        y solo quien logra modificar la fila corre los efectos. Se guarda además
        `status = CLOSED` (si estaba `SCHEDULED`/`OPEN`) para que la base
        cuente lo mismo que la marca.
        """
        now = now or now_utc()
        if shift.closed_effects_applied_at is not None:
            return False
        if self.current_status(shift, now) is not ShiftStatus.CLOSED:
            return False

        claimed = self.session.execute(
            update(Shift)
            .where(Shift.id == shift.id, Shift.closed_effects_applied_at.is_(None))
            .values(closed_effects_applied_at=now)
        ).rowcount
        if claimed == 0:
            self.session.refresh(shift)  # otro request ya lo aplicó: no repetir
            return False

        self.session.refresh(shift)
        for effect in _CLOSE_EFFECTS:
            effect(self.session, shift)
        if shift.status in (ShiftStatus.SCHEDULED, ShiftStatus.OPEN):
            self.shifts.set_status(shift, ShiftStatus.CLOSED)
        return True

    def to_production(
        self,
        shift: Shift,
        actor: User,
        now: datetime | None = None,
        *,
        ip: str | None = None,
    ) -> Shift:
        """El admin decide cuándo arrancar a cocinar: pasa el turno a
        `IN_PRODUCTION`. **Solo lo dispara un admin, nunca el sistema.**

        Solo se puede una vez que cerraron los pedidos (si no, entrarían
        pedidos nuevos a un turno ya en cocina) y una sola vez. Se asegura de
        que los efectos del cierre estén aplicados antes de seguir, aunque
        nadie hubiera consultado el turno desde que cerró.

        Queda en `audit_log`. El paso masivo `PAYMENT_APPROVED` →
        `IN_PREPARATION` de los pedidos del turno se suma cuando existan los
        pedidos (Fase 9).
        """
        now = now or now_utc()
        if actor.role != Role.ADMIN:
            raise ForbiddenError(ONLY_ADMIN)
        if shift.status in _PAST_CLOSING:
            raise InvalidTransitionError(ALREADY_IN_PRODUCTION)
        if self.current_status(shift, now) is not ShiftStatus.CLOSED:
            raise InvalidTransitionError(NOT_CLOSED_YET)

        before = shift.status
        self.on_shift_closed(shift, now)
        self.shifts.set_status(shift, ShiftStatus.IN_PRODUCTION)
        self._audit(
            "shift.to_production",
            shift,
            {"status": before.value},
            {"status": shift.status.value},
            actor,
            ip,
        )
        self.session.flush()
        return shift

    def current_snapshot(self, now: datetime | None = None) -> ShiftSnapshot:
        """Todo lo que el home necesita saber del turno de hoy, en una sola
        pasada con **un único `now`** (así el estado, la ventana y la cuenta
        regresiva son coherentes entre sí).

        Es lo que consulta `GET /shift/current`, así que es también quien
        dispara, de forma perezosa, la creación del turno del día
        (`ensure_today_shift`) y los efectos del cierre (`on_shift_closed`):
        el primer visitante de la jornada / el primero después del cierre.
        """
        now = now or now_utc()
        shift = self.ensure_today_shift(now)
        if shift is None:
            return ShiftSnapshot(now, NO_SERVICE, None, None, False, None)

        self.on_shift_closed(shift, now)
        tz = self.settings.get_timezone()
        window = resolve_window(shift, tz)
        seconds_to_close = max(0, int((window.close_at - now).total_seconds()))
        return ShiftSnapshot(
            now=now,
            status=current_status(shift, now, tz).value,
            shift=shift,
            window=window,
            ordering_open=is_ordering_open(shift, now, tz),
            seconds_to_close=seconds_to_close,
            cancel_deadline_time=to_local(window.cancel_deadline, tz).strftime("%H:%M"),
        )

    # ---------- panel de admin (T-2.4.2) ----------

    def get_shift(self, shift_id: int) -> Shift:
        shift = self.shifts.get_by_id(shift_id)
        if shift is None:
            raise NotFoundError(SHIFT_NOT_FOUND)
        return shift

    def details(self, shifts: list[Shift], now: datetime | None = None) -> list[ShiftDetail]:
        now = now or now_utc()
        tz = self.settings.get_timezone()  # una sola lectura para todo el listado
        return [
            ShiftDetail(
                shift=shift,
                window=resolve_window(shift, tz),
                status=effective_status(shift, now, tz),
                ordering_open=is_ordering_open(shift, now, tz),
            )
            for shift in shifts
        ]

    def detail(self, shift: Shift, now: datetime | None = None) -> ShiftDetail:
        return self.details([shift], now)[0]

    def list_shifts(
        self,
        service_date: date | None = None,
        page: int = 1,
        page_size: int = 20,
        now: datetime | None = None,
    ) -> tuple[list[ShiftDetail], int]:
        """Listado para el admin. Abrir el panel también crea el turno de hoy si
        todavía no existe (§9.9), así que siempre lo encuentra ahí."""
        now = now or now_utc()
        self.ensure_today_shift(now)
        shifts, total = self.shifts.list(service_date, page, page_size)
        return self.details(shifts, now), total

    def update_shift(
        self,
        shift: Shift,
        changes: Mapping[str, Any],
        actor: User,
        *,
        ip: str | None = None,
    ) -> Shift:
        """Ajusta los horarios / la ventana de cancelación de **un turno
        concreto** (la plantilla de los turnos futuros es `shift.default`).

        Solo cambia lo que venga en `changes` (semántica de PATCH), se valida
        contra las mismas reglas que la plantilla mirando el turno **resultante**
        (por ejemplo, adelantar el cierre antes de la apertura falla), y queda
        en `audit_log` con lo anterior y lo nuevo; sin cambio real no se audita.

        Una vez aplicados los efectos del cierre (stock congelado, etc.) ya no
        se pueden tocar la apertura, el cierre ni la ventana de cancelación:
        reabrir un turno no deshace lo que el cierre ya hizo. Las horas
        estimadas (`prep_eta`, `dispatch_eta`) son informativas y siempre se
        pueden corregir.
        """
        if actor.role != Role.ADMIN:
            raise ForbiddenError(ONLY_ADMIN_EDIT)

        current = {
            "open_time": shift.open_time,
            "close_time": shift.close_time,
            "prep_eta": shift.prep_eta,
            "dispatch_eta": shift.dispatch_eta,
            "cancel_window_min": shift.cancel_window_min,
        }
        candidate = {**current, **changes}

        try:
            validated = ShiftSchedule.model_validate(
                {_TO_SCHEDULE_FIELD.get(key, key): value for key, value in candidate.items()}
            )
        except ValidationError as exc:
            fields = [
                {**f, "field": _API_FIELD.get(f["field"], f["field"])}
                for f in fields_from_validation_error(exc)
            ]
            raise DomainValidationError(INVALID_SCHEDULE, {"fields": fields}) from exc

        result = {
            "open_time": validated.open,
            "close_time": validated.close,
            "prep_eta": validated.prep_eta,
            "dispatch_eta": validated.dispatch_eta,
            "cancel_window_min": validated.cancel_window_min,
        }
        changed = [key for key in changes if result[key] != current[key]]
        if not changed:
            return shift  # un PATCH que deja todo igual no ensucia el historial

        locked = shift.closed_effects_applied_at is not None or shift.status in _PAST_CLOSING
        if locked and any(key in _LOCKED_FIELDS for key in changed):
            raise InvalidTransitionError(LOCKED_AFTER_CLOSING)

        for key in changed:
            setattr(shift, key, result[key])
        self._audit(
            "shift.update",
            shift,
            {key: current[key] for key in changed},
            {key: result[key] for key in changed},
            actor,
            ip,
        )
        self.session.flush()
        return shift

    def transition(
        self,
        shift: Shift,
        action: str,
        actor: User,
        now: datetime | None = None,
        *,
        ip: str | None = None,
    ) -> Shift:
        """Acciones manuales del admin sobre el turno: `open`, `close`,
        `to_production`.

        El estado abierto/cerrado se deriva de la hora y no se guarda, así que
        "abrir ahora" y "cerrar ahora" se implementan **moviendo el horario al
        minuto actual** (redondeado hacia abajo, para que el turno ya quede en
        el estado pedido) y no con un estado forzado: hay un solo modelo, y la
        hora que se ve en el turno es la real. Solo sobre el turno de hoy.
        Cerrar aplica además los efectos del cierre en el acto.
        """
        if actor.role != Role.ADMIN:
            raise ForbiddenError(ONLY_ADMIN_EDIT)
        now = now or now_utc()
        if action == "to_production":
            return self.to_production(shift, actor, now, ip=ip)
        if action not in ("open", "close"):
            raise DomainValidationError(
                "Acción desconocida.",
                {
                    "fields": [
                        {"field": "action", "message": "Opciones: open, close, to_production."}
                    ]
                },
            )

        if shift.status in _PAST_CLOSING:
            raise InvalidTransitionError(ALREADY_IN_PRODUCTION)
        tz = self.settings.get_timezone()
        local_now = to_local(now, tz)
        if local_now.date() != shift.service_date:
            raise InvalidTransitionError(NOT_TODAYS_SHIFT)

        status = current_status(shift, now, tz)
        minute = local_now.strftime("%H:%M")  # HH:MM de hora local, redondeado hacia abajo

        if action == "close":
            if status is ShiftStatus.CLOSED:
                raise InvalidTransitionError(ALREADY_CLOSED)
            if status is ShiftStatus.SCHEDULED:
                raise InvalidTransitionError(NOT_OPEN_YET)
            if minute <= shift.open_time:
                raise InvalidTransitionError(CLOSE_TOO_SOON)
            before, shift.close_time = shift.close_time, minute
            self._audit(
                "shift.close", shift, {"close_time": before}, {"close_time": minute}, actor, ip
            )
            self.session.flush()
            self.on_shift_closed(shift, now)  # el cierre ya es <= ahora: se aplica en el acto
        else:
            if status is ShiftStatus.OPEN:
                raise InvalidTransitionError(ALREADY_OPEN)
            if status is ShiftStatus.CLOSED:
                raise InvalidTransitionError(CLOSED_CANNOT_REOPEN)
            before, shift.open_time = shift.open_time, minute
            self._audit(
                "shift.open", shift, {"open_time": before}, {"open_time": minute}, actor, ip
            )
            self.session.flush()
        return shift

    def _audit(
        self,
        action: str,
        shift: Shift,
        before: dict[str, Any],
        after: dict[str, Any],
        actor: User,
        ip: str | None,
    ) -> None:
        self.session.add(
            AuditLog(
                actor_id=actor.id,
                action=action,
                entity_type="shift",
                entity_id=str(shift.id),
                data=json.dumps({"before": before, "after": after}, ensure_ascii=False),
                ip=ip,
            )
        )
