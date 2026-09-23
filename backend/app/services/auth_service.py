from datetime import datetime

from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.enums import AuthProvider, Role, UserStatus
from app.core.errors import (
    ConflictError,
    DomainError,
    ForbiddenError,
    NotAuthenticatedError,
    TokenInvalidError,
)
from app.core.security import (
    create_password_reset_token,
    decode_token,
    hash_password,
    password_fingerprint,
    verify_password,
)
from app.core.timezone import UTC, now_utc
from app.models import Cart, CustomerBalance, RevokedToken, User
from app.repositories.user_repository import UserRepository
from app.services.user_service import normalize_email

EMAIL_TAKEN = "Ya existe una cuenta registrada con ese email."
INVALID_CREDENTIALS = "Email o contraseña incorrectos."
ACCOUNT_NOT_ACTIVE = "Tu cuenta no está habilitada. Contactate con el local."
SESSION_EXPIRED = "Tu sesión expiró. Volvé a iniciar sesión."
RESET_LINK_INVALID = "El link de recuperación no es válido o ya venció. Pedí uno nuevo."

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

    def login_with_google(self, *, sub: str, email: str, first_name: str, last_name: str) -> User:
        """Resuelve el login con Google en sus tres casos posibles.

        1. Ya entró antes con Google (existe el provider) → es esa cuenta.
        2. El email ya tiene cuenta local → se le **vincula** Google, así no
           terminan dos cuentas separadas de la misma persona.
        3. No existe → se crea un CUSTOMER sin contraseña (`password_hash=NULL`)
           con su carrito y su saldo, igual que un registro normal.

        Quien llama debe haber verificado que el email está confirmado por
        Google: vincular con un email sin confirmar permitiría reclamar la
        cuenta de otra persona con solo declarar su dirección.
        """
        email = normalize_email(email)

        linked = self.users.get_provider(AuthProvider.GOOGLE, sub)
        if linked is not None:
            return self._ensure_active(linked.user)

        existing = self.users.get_by_email(email)
        if existing is not None:
            self.users.link_provider(existing, AuthProvider.GOOGLE, provider_uid=sub)
            self.session.flush()
            return self._ensure_active(existing)

        try:
            user = self.users.create(
                first_name=first_name.strip() or email.split("@")[0],
                last_name=last_name.strip() or "-",
                email=email,
                password_hash=None,  # solo entra con Google hasta que use "olvidé mi contraseña"
                role=Role.CUSTOMER,
            )
            self.users.link_provider(user, AuthProvider.GOOGLE, provider_uid=sub)
            user.cart = Cart()
            user.balance = CustomerBalance()
            self.session.flush()
        except IntegrityError as exc:
            self.session.rollback()
            raise ConflictError(EMAIL_TAKEN) from exc

        return user

    def request_password_reset(self, email: str) -> tuple[User, str] | None:
        """Genera el token de recuperación, o `None` si no hay a quién mandarlo.

        Devuelve `None` en silencio (email inexistente o cuenta deshabilitada) y
        el endpoint responde 200 igual: si distinguiera, cualquiera podría
        averiguar qué emails están registrados probando de a uno.
        """
        user = self.users.get_by_email(email)
        if user is None or user.status != UserStatus.ACTIVE:
            return None

        return user, create_password_reset_token(user, user.password_hash)

    def reset_password(self, token: str, new_password: str) -> User:
        """Cambia la contraseña con un token de recuperación, de un solo uso."""
        payload = decode_token(token)  # 401 si venció o está roto

        if payload.get("type") != "password_reset":
            raise TokenInvalidError(RESET_LINK_INVALID)

        jti = payload.get("jti")
        if not jti or self.session.get(RevokedToken, jti) is not None:
            raise TokenInvalidError(RESET_LINK_INVALID)

        user = self.users.get_by_id(int(payload["sub"]))
        if user is None or user.status != UserStatus.ACTIVE:
            raise TokenInvalidError(RESET_LINK_INVALID)

        # Si la contraseña ya cambió desde que se emitió el link, el link muere:
        # evita que un mail viejo reenviado sirva para volver a cambiarla.
        if payload.get("pwd") != password_fingerprint(user.password_hash):
            raise TokenInvalidError(RESET_LINK_INVALID)

        user.password_hash = hash_password(new_password)
        # Una cuenta que venía solo de Google ahora también entra con contraseña.
        self._ensure_local_provider(user)

        try:
            self.revoke_token(payload)  # quema el link usado
        except IntegrityError as exc:
            self.session.rollback()
            raise TokenInvalidError(RESET_LINK_INVALID) from exc

        return user

    def _ensure_local_provider(self, user: User) -> None:
        if not any(p.provider == AuthProvider.LOCAL for p in user.auth_providers):
            self.users.link_provider(user, AuthProvider.LOCAL)

    def _ensure_active(self, user: User) -> User:
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

        try:
            self.revoke_token(payload)
        except IntegrityError as exc:
            # Dos usos del mismo refresh a la vez (dos pestañas, doble click, o
            # un token robado usado en paralelo): los dos pasan el chequeo de
            # arriba y el segundo choca contra la PK. Es exactamente el caso que
            # la rotación quiere frenar → 401, no un 500.
            self.session.rollback()
            raise TokenInvalidError(SESSION_EXPIRED) from exc

        return user

    def logout(self, refresh_token: str | None) -> None:
        """Cierra la sesión quemando el refresh, sin fallar nunca.

        Un logout que devuelve error dejaría al usuario sin forma de cerrar
        sesión: sin cookie, con una vencida, alterada o ya quemada, igual
        termina bien (la cookie se borra en el endpoint). Es idempotente.
        """
        if not refresh_token:
            return

        try:
            payload = decode_token(refresh_token)
        except DomainError:
            return  # vencido, roto o firmado con otra clave: ya no sirve para nada

        if payload.get("type") != "refresh" or not payload.get("jti"):
            return
        if self.session.get(RevokedToken, payload["jti"]) is not None:
            return  # ya estaba quemado

        try:
            self.revoke_token(payload)
        except IntegrityError:
            self.session.rollback()  # otro logout simultáneo ya lo quemó: está bien igual

    def revoke_token(self, payload: dict) -> None:
        """Marca un token como usado/inválido: refresh rotado, logout, o link de
        recuperación ya consumido. Todos guardan su `jti` en la misma tabla."""
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
