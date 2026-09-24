from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, Request, Response

from app.api.deps import AdminUser, SessionDep
from app.core.timezone import now_utc
from app.schemas.shift import (
    ShiftCurrentOut,
    ShiftListOut,
    ShiftOut,
    ShiftTransitionIn,
    ShiftUpdateIn,
)
from app.services.shift_service import ShiftDetail, ShiftService

router = APIRouter(prefix="/shift", tags=["shift"])


def _to_out(detail: ShiftDetail) -> ShiftOut:
    shift, window = detail.shift, detail.window
    return ShiftOut(
        id=shift.id,
        service_date=shift.service_date,
        service_type=shift.service_type.value,
        open_time=shift.open_time,
        close_time=shift.close_time,
        prep_eta=shift.prep_eta,
        dispatch_eta=shift.dispatch_eta,
        cancel_window_min=shift.cancel_window_min,
        status=detail.status.value,
        ordering_open=detail.ordering_open,
        open_at=window.open_at,
        close_at=window.close_at,
        cancel_deadline=window.cancel_deadline,
        closed_effects_applied_at=shift.closed_effects_applied_at,
        updated_at=shift.updated_at,
    )


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


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


@router.get("", response_model=ShiftListOut)
def list_shifts(
    admin: AdminUser,
    session: SessionDep,
    service_date: Annotated[date | None, Query(alias="date")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ShiftListOut:
    """Turnos, del más reciente al más viejo; `?date=YYYY-MM-DD` filtra por día.
    Abrir el panel crea el turno de hoy si todavía no existe."""
    details, total = ShiftService(session).list_shifts(service_date, page, page_size, now_utc())
    return ShiftListOut(
        items=[_to_out(d) for d in details], page=page, page_size=page_size, total=total
    )


@router.patch("/{shift_id}", response_model=ShiftOut)
def update_shift(
    shift_id: int,
    data: ShiftUpdateIn,
    admin: AdminUser,
    session: SessionDep,
    request: Request,
) -> ShiftOut:
    """Ajusta horarios y ventana de cancelación de un turno concreto. Queda en
    `audit_log`. Los cambios a la plantilla de los turnos futuros se hacen en
    `PUT /settings/shift.default`."""
    service = ShiftService(session)
    shift = service.update_shift(
        service.get_shift(shift_id),
        data.model_dump(exclude_unset=True),
        admin,
        ip=_client_ip(request),
    )
    return _to_out(service.detail(shift, now_utc()))


@router.post("/{shift_id}/transition", response_model=ShiftOut)
def transition_shift(
    shift_id: int,
    data: ShiftTransitionIn,
    admin: AdminUser,
    session: SessionDep,
    request: Request,
) -> ShiftOut:
    """Acciones manuales: `open` (abrir ahora), `close` (cerrar ahora) y
    `to_production` (empezar a cocinar). Ver `ShiftService.transition`."""
    service = ShiftService(session)
    now = now_utc()
    shift = service.transition(
        service.get_shift(shift_id), data.action, admin, now, ip=_client_ip(request)
    )
    return _to_out(service.detail(shift, now))
