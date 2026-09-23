from fastapi import APIRouter

from app.api.deps import CurrentUser, SessionDep
from app.schemas.user import MeOut, ProfileUpdateIn
from app.services.user_service import update_profile

router = APIRouter(prefix="/users", tags=["users"])


@router.patch("/me/profile", response_model=MeOut)
def update_my_profile(data: ProfileUpdateIn, user: CurrentUser, session: SessionDep) -> MeOut:
    """Edita nombre, apellido y teléfono del usuario de la sesión.

    Devuelve el usuario completo (igual que `/auth/me`) para que el front
    refresque lo que muestra sin pedirlo de nuevo.
    """
    update_profile(user, data.model_dump(exclude_unset=True))
    session.flush()
    return MeOut.from_user(user)
