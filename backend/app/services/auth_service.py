from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.enums import AuthProvider, Role, UserStatus
from app.core.errors import ConflictError, ForbiddenError, NotAuthenticatedError
from app.core.security import hash_password, verify_password
from app.models import Cart, CustomerBalance, User
from app.repositories.user_repository import UserRepository
from app.services.user_service import normalize_email

EMAIL_TAKEN = "Ya existe una cuenta registrada con ese email."
INVALID_CREDENTIALS = "Email o contraseña incorrectos."
ACCOUNT_NOT_ACTIVE = "Tu cuenta no está habilitada. Contactate con el local."

# Hash descartable para gastar el mismo tiempo cuando el email no existe: sin
# esto, un email inexistente responde muchísimo más rápido que uno real (no
# corre bcrypt) y ese desfase permite averiguar qué emails están registrados.
_DUMMY_HASH = hash_password("contrasena-que-nadie-usa-1")


class AuthService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.users = UserRepository(session)

    def register(
        self,
        *,
        first_name: str,
        last_name: str,
        email: str,
        password: str,
        phone: str | None = None,
    ) -> User:
        """Alta de un cliente con cuenta propia. Espera los datos ya validados
        por el schema del endpoint (T-1.3.2): acá se resuelve la unicidad del
        email y la composición del usuario, no el formato de los campos."""
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
                role=Role.CUSTOMER,
            )
            self.users.link_provider(user, AuthProvider.LOCAL)
            user.cart = Cart()
            user.balance = CustomerBalance()
            self.session.flush()
        except IntegrityError as exc:
            # Dos altas simultáneas con el mismo email pasan las dos el chequeo
            # de arriba y una choca contra el UNIQUE. Sin esto sería un 500.
            # El try cubre desde el create porque el UNIQUE salta en su flush.
            self.session.rollback()
            raise ConflictError(EMAIL_TAKEN) from exc

        return user

    def authenticate(self, *, email: str, password: str) -> User:
        """Valida email + contraseña de una cuenta local.

        El mensaje es el mismo para email inexistente, contraseña incorrecta y
        cuenta que solo entra con Google: decir cuál de los tres falló revelaría
        qué emails están registrados. El estado de la cuenta se chequea
        *después* de verificar la contraseña, así el aviso de cuenta
        deshabilitada solo lo ve quien demostró ser el dueño.
        """
        user = self.users.get_by_email(email)
        expected_hash = user.password_hash if user and user.password_hash else _DUMMY_HASH

        if not verify_password(password, expected_hash) or user is None or not user.password_hash:
            raise NotAuthenticatedError(INVALID_CREDENTIALS)

        if user.status != UserStatus.ACTIVE:
            raise ForbiddenError(ACCOUNT_NOT_ACTIVE)

        return user
