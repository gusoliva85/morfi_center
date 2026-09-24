from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class ShiftCurrentOut(BaseModel):
    """Estado del turno de hoy para el home (§11). Público: no expone nada que
    no se vea ya en la pantalla.

    Los instantes (`now`, `open_at`, `close_at`, `cancel_deadline`) van en UTC
    ya resueltos por el servidor: el front no tiene que hacer cuentas de zona
    horaria ni fiarse del reloj del dispositivo (`seconds_to_close` sale de la
    hora del servidor, no de la del teléfono).

    `status` es `NO_SERVICE` cuando hoy no es día de operación; en ese caso
    todo lo demás, salvo `now`, viene vacío. `ordering_open` es lo que tiene que
    mirar el front para saber si se puede pedir: además del reloj, tiene en
    cuenta que el admin ya haya pasado el turno a producción.
    """

    status: Literal["SCHEDULED", "OPEN", "CLOSED", "NO_SERVICE"]
    now: datetime
    ordering_open: bool
    service_date: date | None = None
    open_time: str | None = None
    close_time: str | None = None
    prep_eta: str | None = None
    open_at: datetime | None = None
    close_at: datetime | None = None
    cancel_deadline: datetime | None = None
    seconds_to_close: int | None = None


class ShiftOut(BaseModel):
    """Un turno para el panel de admin. `status` es el ciclo de vida completo
    (`SCHEDULED`/`OPEN`/`CLOSED` según la hora, o `IN_PRODUCTION`/... si el admin
    ya lo avanzó); `ordering_open` dice si hoy se puede pedir en él."""

    id: int
    service_date: date
    service_type: str
    open_time: str
    close_time: str
    prep_eta: str | None
    dispatch_eta: str | None
    cancel_window_min: int
    status: str
    ordering_open: bool
    open_at: datetime
    close_at: datetime
    cancel_deadline: datetime
    closed_effects_applied_at: datetime | None
    updated_at: datetime


class ShiftListOut(BaseModel):
    items: list[ShiftOut]
    page: int
    page_size: int
    total: int


class ShiftUpdateIn(BaseModel):
    """PATCH de un turno: solo lo que venga se cambia. Los valores se validan en
    el servicio (con las mismas reglas y mensajes que la plantilla), por eso acá
    son `Any`; los campos desconocidos sí se rechazan."""

    model_config = ConfigDict(extra="forbid")

    open_time: Any = None
    close_time: Any = None
    prep_eta: Any = None
    dispatch_eta: Any = None
    cancel_window_min: Any = None


class ShiftTransitionIn(BaseModel):
    action: Literal["open", "close", "to_production"]
