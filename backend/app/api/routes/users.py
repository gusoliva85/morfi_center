"""Endpoints de perfil del propio usuario y, para admins, gestión de personal."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.core.enums import Role
from app.db.session import get_session
from app.models.user import User
from app.schemas.user import (
    CreateStaffIn,
    CreateStaffOut,
    UpdateProfileIn,
    UpdateUserIn,
    UserListOut,
    UserOut,
)
from app.services import user_service
from app.services.auth_service import AuthService

router = APIRouter(prefix="/users", tags=["users"])


@router.patch("/me/profile", response_model=UserOut)
def update_my_profile(
    payload: UpdateProfileIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> UserOut:
    """Actualiza `first_name`/`last_name`/`phone` del usuario logueado.

    PATCH parcial: solo se tocan los campos presentes en el body. `email`
    no es editable por acá.
    """
    updates = payload.model_dump(exclude_unset=True)
    user_service.update_profile(user, updates)
    db.flush()
    return UserOut.model_validate(user)


@router.post("", response_model=CreateStaffOut, status_code=status.HTTP_201_CREATED)
def create_staff(
    payload: CreateStaffIn,
    _admin: User = Depends(require_role(Role.ADMIN)),
    db: Session = Depends(get_session),
) -> CreateStaffOut:
    """Alta de personal (`ADMIN`/`DELIVERY`), solo para admins. Ver
    `AuthService.create_staff` — no emite tokens, no auto-loguea."""
    user, temporary_password = AuthService(db).create_staff(
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        role=payload.role,
        phone=payload.phone,
        password=payload.password,
        vehicle_type=payload.vehicle_type,
        capacity=payload.capacity,
    )
    return CreateStaffOut(
        **UserOut.model_validate(user).model_dump(),
        temporary_password=temporary_password,
    )


@router.get("", response_model=UserListOut)
def list_users(
    role: Role | None = Query(default=None),
    page: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=100),
    _admin: User = Depends(require_role(Role.ADMIN)),
    db: Session = Depends(get_session),
) -> UserListOut:
    """Listado paginado de usuarios, solo para admins. `?role=` filtra."""
    result = AuthService(db).list_users(role=role, page=page, page_size=page_size)
    return UserListOut(
        items=[UserOut.model_validate(u) for u in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
    )


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UpdateUserIn,
    request: Request,
    admin: User = Depends(require_role(Role.ADMIN)),
    db: Session = Depends(get_session),
) -> UserOut:
    """Edita `role` y/o `status` de otro usuario, solo para admins. Queda
    auditado en `audit_log` (ver `AuthService.update_user`)."""
    user = AuthService(db).update_user(
        actor=admin,
        target_id=user_id,
        role=payload.role,
        status=payload.status,
        ip=request.client.host if request.client else None,
    )
    return UserOut.model_validate(user)


__all__ = ["router"]
