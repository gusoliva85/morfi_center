from datetime import datetime

from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.enums import AuthProvider, Role, UserStatus
from app.core.errors import (
    ConflictError,
    ForbiddenError,
    NotAuthenticatedError,
    TokenInvalidError,
)
from app.core.security import decode_token, hash_password, verify_password
from app.core.timezone import UTC, now_utc
from app.models import Cart, CustomerBalance, RevokedToken, User
from app.repositories.user_repository import UserRepository
from app.services.user_service import normalize_email

EMAIL_TAKEN = "Ya existe una cuenta registrada con ese email."
INVALID_CREDENTIALS = "Email o contraseña incorrectos."
ACCOUNT_NOT_ACTIVE = "Tu cuenta no está habilitada. Contactate con el local."
SESSION_EXPIRED = "Tu sesión expiró. Volvé a iniciar sesión."

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

    def rotate_refresh(self, refresh_token: str) -> User:
        """Valida un refresh token y lo quema: el mismo token no sirve dos veces.

        Rotación en un solo uso — si alguien roba la cookie, en cuanto el dueño
        legítimo refresca, el token robado deja de funcionar (y al revés, lo que
        deja rastro de que algo pasó). Devuelve el usuario para que el endpoint
        emita el access nuevo y la cookie nueva.
        """
        payload = decode_token(refresh_token)  # lanza 401 si está vencido o roto

        if payload.get("type") != "refresh":
            raise TokenInvalidError(SESSION_EXPIRED)

        jti = payload.get("jti")
        if not jti or self.session.get(RevokedToken, jti) is not None:
            raise TokenInvalidError(SESSION_EXPIRED)

        user = self.users.get_by_id(int(payload["sub"]))
        if user is None:
            raise TokenInvalidError(SESSION_EXPIRED)
        if user.status != UserStatus.ACTIVE:
            raise ForbiddenError(ACCOUNT_NOT_ACTIVE)

        self.revoke_refresh(payload)
        return user

    def revoke_refresh(self, payload: dict) -> None:
        """Marca un refresh como usado/inválido (rotación y logout)."""
        self._purge_expired_revocations()
        self.session.add(
            RevokedToken(
                jti=payload["jti"],
                expires_at=datetime.fromtimestamp(payload["exp"], tz=UTC),
            )
        )
        self.session.flush()

    def _purge_expired_revocations(self) -> None:
        """Las revocaciones de tokens ya vencidos no aportan nada (el token falla
        igual por vencido), así que se borran para que la tabla no crezca sin
        límite: cada refresh agregaría una fila para siempre."""
        self.session.execute(delete(RevokedToken).where(RevokedToken.expires_at < now_utc()))
