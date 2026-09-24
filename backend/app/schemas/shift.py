from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel


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
