from fastapi import APIRouter, status

from app.api.deps import AdminUser, CurrentUser, SessionDep
from app.schemas.user import MeOut, ProfileUpdateIn, StaffCreateIn, UserOut
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


@router.patch("/me/profile", response_model=MeOut)
def update_my_profile(data: ProfileUpdateIn, user: CurrentUser, session: SessionDep) -> MeOut:
    """Edita nombre, apellido y teléfono del usuario de la sesión.

    Devuelve el usuario completo (igual que `/auth/me`) para que el front
    refresque lo que muestra sin pedirlo de nuevo.
    """
    update_profile(user, data.model_dump(exclude_unset=True))
    session.flush()
    return MeOut.from_user(user)
