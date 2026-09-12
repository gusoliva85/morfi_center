"""Acceso a datos de turnos (ver `app/models/shift.py`).

Nunca comitea, solo `flush()`. No conoce zonas horarias ni "ahora": recibe
`service_date` como texto `'YYYY-MM-DD'` ya resuelto por quien llama
(`ShiftService`, Tema 2.2) — mantiene la capa de datos libre de lógica de
tiempo.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import ServiceType, ShiftStatus
from app.models.shift import Shift


class ShiftRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_date_type(
        self, service_date: str, service_type: ServiceType = ServiceType.LUNCH
    ) -> Shift | None:
        stmt = select(Shift).where(
            Shift.service_date == service_date, Shift.service_type == service_type
        )
        return self.session.scalars(stmt).first()

    def get_current(
        self, service_date: str, service_type: ServiceType = ServiceType.LUNCH
    ) -> Shift | None:
        """Atajo de `get_by_date_type` con el `service_type` por defecto del
        MVP (un único turno `LUNCH` por día)."""
        return self.get_by_date_type(service_date, service_type)

    def create_from_default(
        self,
        *,
        service_date: str,
        open_time: str,
        close_time: str,
        prep_eta: str | None = None,
        dispatch_eta: str | None = None,
        cancel_window_min: int = 20,
        service_type: ServiceType = ServiceType.LUNCH,
    ) -> Shift:
        """Crea el turno de una fecha a partir de una plantilla (los
        defaults de `SettingKey.SHIFT_DEFAULT`, ver `ShiftService`).

        No valida que ya exista uno para esa fecha+tipo — eso lo hace quien
        llama (`ShiftService.ensure_today_shift`, Tema 2.2), que decide qué
        significa "ya existe" en su flujo idempotente.
        """
        shift = Shift(
            service_date=service_date,
            service_type=service_type,
            open_time=open_time,
            close_time=close_time,
            prep_eta=prep_eta,
            dispatch_eta=dispatch_eta,
            cancel_window_min=cancel_window_min,
        )
        self.session.add(shift)
        self.session.flush()
        return shift

    def set_status(self, shift: Shift, status: ShiftStatus) -> Shift:
        shift.status = status
        self.session.flush()
        return shift


__all__ = ["ShiftRepository"]
