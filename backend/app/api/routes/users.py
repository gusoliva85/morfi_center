from typing import Annotated

from fastapi import APIRouter, Query, Request, status

from app.api.deps import AdminUser, CurrentUser, SessionDep
from app.core.enums import Role
from app.schemas.user import (
    MeOut,
    ProfileUpdateIn,
    StaffCreateIn,
    UserListOut,
    UserOut,
    UserUpdateIn,
)
from app.services.user_admin_service import UserAdminService
from app.services.user_service import update_profile

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_staff(data: StaffCreateIn, admin: AdminUser, session: SessionDep) -> UserOut:
    """Alta de ADMIN o DELIVERY, solo para admins. No devuelve tokens: el
    usuario nuevo entra por su cuenta con las credenciales que le pasen."""
    user = UserAdminService(session).create_staff(
        role=data.role,
        first_name=data.first_name,
        last_name=data.last_name,
        email=data.email,
        password=data.password,
        phone=data.phone,
        vehicle_type=data.vehicle_type.value if data.vehicle_type else None,
        capacity=data.capacity,
    )
    return UserOut.model_validate(user)


@router.get("", response_model=UserListOut)
def list_users(
    admin: AdminUser,
    session: SessionDep,
    role: Role | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> UserListOut:
    """Listado paginado para el panel de admin, con filtro por rol.

    `page_size` está topeado: sin tope, un `?page_size=999999` traería la tabla
    entera en una sola respuesta.
    """
    users, total = UserAdminService(session).list_users(role=role, page=page, page_size=page_size)
    return UserListOut(
        items=[UserOut.model_validate(u) for u in users],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    data: UserUpdateIn,
    admin: AdminUser,
    session: SessionDep,
    request: Request,
) -> UserOut:
    """Cambia el rol o el estado de un usuario. Queda registrado en `audit_log`
    con quién lo hizo, los valores anteriores y los nuevos."""
    user = UserAdminService(session).update_user(
        user_id,
        data.model_dump(exclude_unset=True),
        actor=admin,
        ip=request.client.host if request.client else None,
    )
    return UserOut.model_validate(user)


@router.patch("/me/profile", response_model=MeOut)
def update_my_profile(data: ProfileUpdateIn, user: CurrentUser, session: SessionDep) -> MeOut:
    """Edita nombre, apellido y teléfono del usuario de la sesión.

    Devuelve el usuario completo (igual que `/auth/me`) para que el front
    refresque lo que muestra sin pedirlo de nuevo.
    """
    update_profile(user, data.model_dump(exclude_unset=True))
    session.flush()
    return MeOut.from_user(user)
