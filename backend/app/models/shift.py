from datetime import date

from sqlalchemy import CheckConstraint, Date, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import ServiceType, ShiftStatus
from app.db.base import Base
from app.db.types import TimestampMixin, enum_column


class Shift(TimestampMixin, Base):
    """Un turno de servicio (§6.4): la ventana en la que se puede pedir.

    Los horarios (`open_time`, `close_time`, `prep_eta`, `dispatch_eta`) son
    hora de pared **local** en texto `HH:MM`, no instantes: convertirlos a UTC
    es trabajo de `ShiftService` (T-2.2.2), que usa la zona horaria de
    configuración. `service_date` es la fecha local del servicio.

    `status` guarda solo lo que hay que recordar. Que el turno esté por abrir,
    abierto o cerrado **no se guarda**: se deriva de la hora (§9.9); por eso
    `SCHEDULED`/`OPEN`/`CLOSED` conviven en el enum pero el resto del ciclo
    (`IN_PRODUCTION`, `DISPATCHING`, `FINISHED`) es lo que realmente cambia
    por una acción del admin.
    """

    __tablename__ = "shifts"
    __table_args__ = (
        UniqueConstraint("service_date", "service_type", name="uq_shifts_date_type"),
        CheckConstraint("cancel_window_min >= 0", name="cancel_window_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    service_date: Mapped[date] = mapped_column(Date, nullable=False)
    service_type: Mapped[ServiceType] = mapped_column(
        enum_column(ServiceType, "service_type"), nullable=False, default=ServiceType.LUNCH
    )
    open_time: Mapped[str] = mapped_column(String, nullable=False)
    close_time: Mapped[str] = mapped_column(String, nullable=False)
    prep_eta: Mapped[str | None] = mapped_column(String)
    dispatch_eta: Mapped[str | None] = mapped_column(String)
    cancel_window_min: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    status: Mapped[ShiftStatus] = mapped_column(
        enum_column(ShiftStatus, "shift_status"), nullable=False, default=ShiftStatus.SCHEDULED
    )
