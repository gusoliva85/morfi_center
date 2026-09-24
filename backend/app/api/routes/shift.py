from fastapi import APIRouter, Response

from app.api.deps import SessionDep
from app.core.timezone import now_utc
from app.schemas.shift import ShiftCurrentOut
from app.services.shift_service import ShiftService

router = APIRouter(prefix="/shift", tags=["shift"])


@router.get("/current", response_model=ShiftCurrentOut)
def current_shift(session: SessionDep, response: Response) -> ShiftCurrentOut:
    """Estado del turno de hoy. Público (lo consulta el home, con o sin sesión).

    El primer pedido de la jornada crea el turno con la plantilla, y el primero
    después del cierre aplica los efectos del cierre: no hay ningún job.
    """
    # La respuesta lleva la hora del servidor: cachearla la volvería mentira.
    response.headers["Cache-Control"] = "no-store"

    snapshot = ShiftService(session).current_snapshot(now_utc())
    shift, window = snapshot.shift, snapshot.window
    return ShiftCurrentOut(
        status=snapshot.status,
        now=snapshot.now,
        ordering_open=snapshot.ordering_open,
        service_date=shift.service_date if shift else None,
        open_time=shift.open_time if shift else None,
        close_time=shift.close_time if shift else None,
        prep_eta=shift.prep_eta if shift else None,
        open_at=window.open_at if window else None,
        close_at=window.close_at if window else None,
        cancel_deadline=window.cancel_deadline if window else None,
        seconds_to_close=snapshot.seconds_to_close,
    )
