from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.enums import ShiftStatus
from app.core.timezone import now_utc, resolve_shift_instant
from app.models import Shift
from app.services.settings_service import SettingsService

# Estados que solo existen porque un admin los puso a mano: una vez ahí, el
# turno ya no acepta pedidos aunque el reloj diga otra cosa.
_PAST_CLOSING = (ShiftStatus.IN_PRODUCTION, ShiftStatus.DISPATCHING, ShiftStatus.FINISHED)


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

    def resolve_window(self, shift: Shift) -> ShiftWindow:
        return resolve_window(shift, self.settings.get_timezone())

    def current_status(self, shift: Shift, now: datetime | None = None) -> ShiftStatus:
        return current_status(shift, now or now_utc(), self.settings.get_timezone())

    def is_ordering_open(self, shift: Shift, now: datetime | None = None) -> bool:
        return is_ordering_open(shift, now or now_utc(), self.settings.get_timezone())
