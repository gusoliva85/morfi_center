from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import ServiceType, ShiftStatus
from app.models import Shift
from app.schemas.settings import ShiftDefault


class ShiftRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_date_type(
        self, service_date: date, service_type: ServiceType = ServiceType.LUNCH
    ) -> Shift | None:
        return self.session.scalar(
            select(Shift).where(
                Shift.service_date == service_date, Shift.service_type == service_type
            )
        )

    def get_current(
        self, today: date, service_type: ServiceType = ServiceType.LUNCH
    ) -> Shift | None:
        """El turno que se está sirviendo hoy (`today` es la fecha **local**,
        que el repositorio no calcula: no sabe de zonas horarias). Hoy es
        exactamente el de la fecha; queda como método aparte porque con más de
        un turno por día "el actual" dejará de ser solo una búsqueda por fecha."""
        return self.get_by_date_type(today, service_type)

    def create_from_default(
        self,
        service_date: date,
        template: ShiftDefault,
        service_type: ServiceType = ServiceType.LUNCH,
    ) -> Shift:
        """Crea el turno del día copiando la plantilla (`shift.default`).

        No mira `template.weekdays`: decidir si ese día se opera es de
        `ShiftService.ensure_today_shift` (T-2.2.3). Una copia, no una
        referencia: cambiar la plantilla después no altera turnos ya creados.

        Si ya existía uno para esa fecha y tipo, el `UNIQUE` hace fallar el
        `flush` con `IntegrityError` — quien lo llama es quien sabe cómo
        resolver esa carrera.
        """
        shift = Shift(
            service_date=service_date,
            service_type=service_type,
            open_time=template.open,
            close_time=template.close,
            prep_eta=template.prep_eta,
            dispatch_eta=template.dispatch_eta,
            cancel_window_min=template.cancel_window_min,
            status=ShiftStatus.SCHEDULED,
        )
        self.session.add(shift)
        self.session.flush()
        return shift

    def set_status(self, shift: Shift, status: ShiftStatus) -> Shift:
        """Cambia el estado guardado. No valida la transición: las reglas de qué
        estado puede seguir a cuál son de `ShiftService` (T-2.2.4)."""
        shift.status = status
        self.session.flush()
        return shift
