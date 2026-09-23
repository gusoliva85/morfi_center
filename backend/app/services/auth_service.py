from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.enums import AuthProvider, Role
from app.core.errors import ConflictError
from app.core.security import hash_password
from app.models import Cart, CustomerBalance, User
from app.repositories.user_repository import UserRepository
from app.services.user_service import normalize_email

EMAIL_TAKEN = "Ya existe una cuenta registrada con ese email."


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
