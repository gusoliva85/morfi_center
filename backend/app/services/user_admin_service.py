import json
from collections.abc import Mapping

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.enums import AuthProvider, DriverStatus, Role, UserStatus
from app.core.errors import ConflictError, ForbiddenError, NotFoundError
from app.core.security import hash_password
from app.models import AuditLog, Cart, CustomerBalance, User, UserProfile
from app.repositories.user_repository import UserRepository
from app.services.user_service import normalize_email

EMAIL_TAKEN = "Ya existe una cuenta registrada con ese email."
ONLY_STAFF = "Por acá solo se crean usuarios ADMIN o DELIVERY."
CANNOT_EDIT_SELF = "No podés cambiar tu propio rol ni tu propio estado."
USER_NOT_FOUND = "No existe ese usuario."


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

    def list_users(
        self, role: Role | None = None, page: int = 1, page_size: int = 20
    ) -> tuple[list[User], int]:
        return self.users.list(role=role, page=page, page_size=page_size)

    def update_user(
        self,
        user_id: int,
        changes: Mapping[str, Role | UserStatus],
        *,
        actor: User,
        ip: str | None = None,
    ) -> User:
        """Cambia rol y/o estado de un usuario, dejando rastro en `audit_log`.

        Solo aplica lo que venga en `changes` (semántica de PATCH) y **no se
        audita nada si no hubo cambio real**: auditar un PATCH que dejó todo
        igual llenaría el log de ruido y escondería los cambios de verdad.
        """
        user = self.users.get_by_id(user_id)
        if user is None:
            raise NotFoundError(USER_NOT_FOUND)

        # Un admin que se suspende o se baja de rol a sí mismo se queda afuera
        # en el acto, sin manera de revertirlo desde la app.
        if user.id == actor.id:
            raise ForbiddenError(CANNOT_EDIT_SELF)

        before: dict[str, str] = {}
        after: dict[str, str] = {}

        if "role" in changes and changes["role"] != user.role:
            before["role"], after["role"] = user.role.value, changes["role"].value
            user.role = changes["role"]
            if user.role == Role.CUSTOMER:
                self._ensure_customer_records(user)

        if "status" in changes and changes["status"] != user.status:
            before["status"], after["status"] = user.status.value, changes["status"].value
            user.status = changes["status"]

        if after:
            self._audit(
                action="user.update",
                entity_id=str(user.id),
                data={"before": before, "after": after},
                actor=actor,
                ip=ip,
            )

        self.session.flush()
        return user

    def _ensure_customer_records(self, user: User) -> None:
        """Un usuario que pasa a CUSTOMER necesita carrito y saldo: sin ellos
        quedaría como cliente a medias, sin poder pedir nada."""
        if user.cart is None:
            user.cart = Cart()
        if user.balance is None:
            user.balance = CustomerBalance()

    def _audit(
        self,
        *,
        action: str,
        entity_id: str,
        data: dict,
        actor: User,
        ip: str | None,
    ) -> None:
        self.session.add(
            AuditLog(
                actor_id=actor.id,
                action=action,
                entity_type="user",
                entity_id=entity_id,
                data=json.dumps(data, ensure_ascii=False),
                ip=ip,
            )
        )
