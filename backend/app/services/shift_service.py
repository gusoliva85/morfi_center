import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.enums import Role, ShiftStatus
from app.core.errors import ForbiddenError, InvalidTransitionError
from app.core.timezone import now_utc, resolve_shift_instant, to_local
from app.models import AuditLog, Shift, User
from app.repositories.shift_repository import ShiftRepository
from app.services.settings_service import SettingsService

ONLY_ADMIN = "Solo un administrador puede pasar el turno a producción."
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
        self.session.add(
            AuditLog(
                actor_id=actor.id,
                action="shift.to_production",
                entity_type="shift",
                entity_id=str(shift.id),
                data=json.dumps({"before": before.value, "after": shift.status.value}),
                ip=ip,
            )
        )
        self.session.flush()
        return shift
