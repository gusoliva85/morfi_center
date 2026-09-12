"""Turnos de servicio (`documentacion/02_Documento_Tecnico.md` §6.4).

`service_date`/`open_time`/`close_time`/`prep_eta`/`dispatch_eta` son texto
plano en **hora local** (no UTC): resolverlos a instantes UTC concretos es
responsabilidad de `ShiftService.resolve_window` (Tema 2.2), que conoce la
zona horaria de operación (`system_settings.timezone`) — el modelo no.
"""

from __future__ import annotations

from sqlalchemy import Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import ServiceType, ShiftStatus
from app.db.base import Base, TimestampMixin
from app.db.types import sa_enum


class Shift(Base, TimestampMixin):
    """Un turno de servicio para una fecha (a lo sumo uno por fecha+tipo)."""

    __tablename__ = "shifts"
    __table_args__ = (UniqueConstraint("service_date", "service_type"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    service_date: Mapped[str] = mapped_column(
        String(10), nullable=False, index=True
    )  # 'YYYY-MM-DD'
    service_type: Mapped[ServiceType] = mapped_column(
        sa_enum(ServiceType), nullable=False, default=ServiceType.LUNCH
    )
    open_time: Mapped[str] = mapped_column(String(5), nullable=False)  # 'HH:MM'
    close_time: Mapped[str] = mapped_column(String(5), nullable=False)
    prep_eta: Mapped[str | None] = mapped_column(String(5))
    dispatch_eta: Mapped[str | None] = mapped_column(String(5))
    cancel_window_min: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    status: Mapped[ShiftStatus] = mapped_column(
        sa_enum(ShiftStatus), nullable=False, default=ShiftStatus.SCHEDULED
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"Shift(service_date={self.service_date!r}, "
            f"service_type={self.service_type!r}, status={self.status!r})"
        )


__all__ = ["Shift"]
