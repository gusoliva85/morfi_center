from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.enums import AuthProvider, DriverStatus, Role
from app.core.errors import ConflictError, ForbiddenError
from app.core.security import hash_password
from app.models import User, UserProfile
from app.repositories.user_repository import UserRepository
from app.services.user_service import normalize_email

EMAIL_TAKEN = "Ya existe una cuenta registrada con ese email."
ONLY_STAFF = "Por acá solo se crean usuarios ADMIN o DELIVERY."


class UserAdminService:
    """Lo que un admin hace sobre *otros* usuarios.

    Va en su propio módulo y no en `user_service.py`: ese módulo son reglas
    puras y lo importa `UserRepository`, así que meter acá el repositorio
    cerraría un círculo (repositorios están debajo de servicios, no al lado).
    """

    def __init__(self, session: Session) -> None:
        self.session = session
        self.users = UserRepository(session)

    def create_staff(
        self,
        *,
        role: Role,
        first_name: str,
        last_name: str,
        email: str,
        password: str,
        phone: str | None = None,
        vehicle_type: str | None = None,
        capacity: int | None = None,
    ) -> User:
        """Da de alta un ADMIN o un DELIVERY. Sin auto-login: la sesión la abre
        la persona cuando entra con sus credenciales.

        No crea carrito ni saldo (son de clientes, `T-1.2.2`), y a los DELIVERY
        les crea su `UserProfile` con `driver_status=NO_DISPONIBLE`: un
        repartidor recién creado no debería aparecer como disponible para
        asignarle pedidos antes de empezar su turno (Fase 14).
        """
        if role not in (Role.ADMIN, Role.DELIVERY):
            raise ForbiddenError(ONLY_STAFF)  # los CUSTOMER se registran solos

        email = normalize_email(email)
        if self.users.get_by_email(email) is not None:
            raise ConflictError(EMAIL_TAKEN)

        try:
            user = self.users.create(
                first_name=first_name.strip(),
                last_name=last_name.strip(),
                email=email,
                password_hash=hash_password(password),
                phone=phone.strip() if phone else None,
                role=role,
            )
            self.users.link_provider(user, AuthProvider.LOCAL)
            if role == Role.DELIVERY:
                user.profile = UserProfile(
                    vehicle_type=vehicle_type,
                    capacity=capacity,
                    driver_status=DriverStatus.NO_DISPONIBLE,
                )
            self.session.flush()
        except IntegrityError as exc:
            # Misma carrera que en el registro: dos altas simultáneas con el
            # mismo email pasan el chequeo previo y una choca contra el UNIQUE.
            self.session.rollback()
            raise ConflictError(EMAIL_TAKEN) from exc

        return user
