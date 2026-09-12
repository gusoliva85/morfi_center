"""Lógica de autenticación: registro (Tema 1.3), login local (Tema 1.4),
gestión de usuarios por un admin (Tema 1.7) y recuperación de contraseña
(Tema 1.9)."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.enums import AuthProvider, Role, UserStatus, VehicleType
from app.core.errors import (
    ConflictError,
    ForbiddenError,
    InvalidInputError,
    NotAuthenticatedError,
    NotFoundError,
)
from app.core.security import (
    TokenError,
    create_password_reset_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.balance import CustomerBalance
from app.models.cart import Cart
from app.models.user import User, UserProfile
from app.repositories.audit_repository import AuditLogRepository
from app.repositories.pagination import Page
from app.repositories.token_repository import TokenRepository
from app.repositories.user_repository import UserRepository
from app.services import user_service

_STAFF_ROLES = (Role.ADMIN, Role.DELIVERY)

# Mensaje único para toda razón por la que una sesión no es válida (ausente,
# expirada, con firma inválida o un refresh ya rotado) — no distinguir el
# motivo evita darle pistas a quien intenta reusar/adivinar un token.
_SESSION_INVALID_MESSAGE = "La sesión expiró o no es válida. Iniciá sesión de nuevo."


class AuthService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.tokens = TokenRepository(session)
        self.audit = AuditLogRepository(session)

    def register(
        self,
        *,
        first_name: str,
        last_name: str,
        email: str,
        password: str,
        phone: str | None = None,
    ) -> User:
        """Alta de cuenta propia (rol ``CUSTOMER``).

        Valida la forma de cada dato, normaliza email y teléfono, verifica que
        el email no esté en uso, y crea en la misma unidad de trabajo: el
        usuario, su proveedor de auth ``local``, su carrito y su saldo en 0.
        No hace commit — eso lo decide quien abrió la sesión.

        :raises InvalidInputError: si algún dato no cumple su formato
            (propagado desde ``user_service``).
        :raises ConflictError: si ya existe una cuenta con ese email.
        """
        clean_first = user_service.validate_person_name(first_name, field="first_name")
        clean_last = user_service.validate_person_name(last_name, field="last_name")
        clean_email = user_service.normalize_email(email)
        clean_phone = user_service.normalize_phone(phone)
        user_service.validate_password(password)

        if self.users.get_by_email(clean_email) is not None:
            raise ConflictError(
                "Ya existe una cuenta registrada con ese email.",
                details={"field": "email"},
            )

        user = self.users.create(
            first_name=clean_first,
            last_name=clean_last,
            email=clean_email,
            phone=clean_phone,
            password_hash=hash_password(password),
            role=Role.CUSTOMER,
        )
        self.users.link_provider(user, AuthProvider.LOCAL)

        # Todavía no hay CartRepository / BalanceRepository (llegan en las
        # Fases 6 y 12): por ahora es la propia sesión la que los persiste.
        self.session.add(Cart(user_id=user.id))
        self.session.add(CustomerBalance(user_id=user.id))
        self.session.flush()

        return user

    def login_with_google(
        self,
        *,
        sub: str,
        email: str,
        first_name: str,
        last_name: str,
    ) -> User:
        """Login/alta vía Google OIDC (ver `02_Documento_Tecnico.md` §13.3).

        Tres caminos, en este orden:
        1. Ya existe ``user_auth_providers(google, sub)``: es un login, se
           devuelve ese usuario.
        2. No existe el provider pero sí un usuario con ese email (alta local
           previa, o de personal): se **vincula** el provider `google` a esa
           cuenta — no toca su contraseña.
        3. Ninguno de los dos existe: se crea un ``CUSTOMER`` nuevo
           (``password_hash=NULL`` — solo puede loguearse con Google) junto
           con su provider, carrito y saldo, igual que ``register`` pero sin
           contraseña.

        En los tres casos, si la cuenta resultante no está ``ACTIVE``, se
        rechaza igual que en ``authenticate``.

        :raises ForbiddenError: la cuenta existe pero no está ``ACTIVE``.
        """
        existing_provider = self.users.get_provider(AuthProvider.GOOGLE, sub)
        if existing_provider is not None:
            user = existing_provider.user
        else:
            clean_email = user_service.normalize_email(email)
            user = self.users.get_by_email(clean_email)
            if user is not None:
                self.users.link_provider(user, AuthProvider.GOOGLE, provider_uid=sub)
            else:
                clean_first = user_service.validate_person_name(first_name, field="first_name")
                clean_last = user_service.validate_person_name(last_name, field="last_name")
                user = self.users.create(
                    first_name=clean_first,
                    last_name=clean_last,
                    email=clean_email,
                    password_hash=None,
                    role=Role.CUSTOMER,
                )
                self.users.link_provider(user, AuthProvider.GOOGLE, provider_uid=sub)
                self.session.add(Cart(user_id=user.id))
                self.session.add(CustomerBalance(user_id=user.id))

        if user.status != UserStatus.ACTIVE:
            raise ForbiddenError("Esta cuenta no está activa. Contactá al administrador.")

        self.session.flush()
        return user

    def create_staff(
        self,
        *,
        first_name: str,
        last_name: str,
        email: str,
        role: Role,
        phone: str | None = None,
        password: str | None = None,
        vehicle_type: VehicleType | None = None,
        capacity: int | None = None,
    ) -> tuple[User, str | None]:
        """Alta de personal (``ADMIN``/``DELIVERY``) hecha por un admin.

        A diferencia de ``register``: no emite tokens (la persona inicia
        sesión después, con sus propias credenciales) y no crea carrito ni
        saldo (son conceptos de cliente). Para ``DELIVERY`` sí crea el
        ``UserProfile`` con los datos del vehículo.

        Si no se pasa ``password``, se genera una temporal aleatoria y se
        devuelve en texto plano junto con el usuario — es la única vez que
        está disponible; todavía no hay envío de mail (ver T-1.9.1), así que
        el admin se la comunica a la persona por fuera del sistema.

        :raises InvalidInputError: si ``role`` no es ``ADMIN``/``DELIVERY``,
            o algún dato no cumple su formato.
        :raises ConflictError: si ya existe una cuenta con ese email.
        """
        if role not in _STAFF_ROLES:
            raise InvalidInputError("El rol debe ser ADMIN o DELIVERY.", details={"field": "role"})

        clean_first = user_service.validate_person_name(first_name, field="first_name")
        clean_last = user_service.validate_person_name(last_name, field="last_name")
        clean_email = user_service.normalize_email(email)
        clean_phone = user_service.normalize_phone(phone)

        if self.users.get_by_email(clean_email) is not None:
            raise ConflictError(
                "Ya existe una cuenta registrada con ese email.",
                details={"field": "email"},
            )

        generated_password: str | None = None
        if password:
            user_service.validate_password(password)
            plain_password = password
        else:
            plain_password = secrets.token_urlsafe(9)
            generated_password = plain_password

        user = self.users.create(
            first_name=clean_first,
            last_name=clean_last,
            email=clean_email,
            phone=clean_phone,
            password_hash=hash_password(plain_password),
            role=role,
        )
        self.users.link_provider(user, AuthProvider.LOCAL)

        if role == Role.DELIVERY:
            self.session.add(
                UserProfile(user_id=user.id, vehicle_type=vehicle_type, capacity=capacity)
            )

        self.session.flush()
        return user, generated_password

    def list_users(
        self,
        *,
        role: Role | None = None,
        page: int | None = None,
        page_size: int | None = None,
    ) -> Page[User]:
        """Listado paginado de usuarios, opcionalmente filtrado por rol."""
        return self.users.list(role=role, page=page, page_size=page_size)

    def update_user(
        self,
        *,
        actor: User,
        target_id: int,
        role: Role | None = None,
        status: UserStatus | None = None,
        ip: str | None = None,
    ) -> User:
        """Un admin edita el rol y/o el estado de otro usuario. Audita el
        cambio en ``audit_log`` (before/after de ambos campos).

        :raises NotFoundError: si ``target_id`` no existe.
        :raises InvalidInputError: si no se manda ni ``role`` ni ``status``.
        """
        if role is None and status is None:
            raise InvalidInputError("Hay que indicar `role` y/o `status` para actualizar.")

        user = self.users.get_by_id(target_id)
        if user is None:
            raise NotFoundError("El usuario no existe.")

        before = {"role": user.role.value, "status": user.status.value}
        if role is not None:
            user.role = role
        if status is not None:
            user.status = status
        after = {"role": user.role.value, "status": user.status.value}

        self.audit.record(
            actor_id=actor.id,
            action="user.update_role_status",
            entity_type="user",
            entity_id=str(user.id),
            data={"before": before, "after": after},
            ip=ip,
        )
        self.session.flush()
        return user

    def authenticate(self, email: str, password: str) -> User:
        """Verifica credenciales de login local.

        El mensaje ante email inexistente o contraseña incorrecta es
        **idéntico a propósito** (no revela cuál de los dos falló, ni si el
        email está registrado). La cuenta suspendida/inactiva sí se informa
        aparte, pero solo después de validar la contraseña — así una cuenta
        suspendida no se puede detectar probando contraseñas al azar.

        :raises NotAuthenticatedError: email inexistente o contraseña incorrecta.
        :raises ForbiddenError: credenciales correctas pero la cuenta no está ACTIVE.
        """
        clean_email = user_service.normalize_email(email)
        user = self.users.get_by_email(clean_email)
        if user is None or not verify_password(password, user.password_hash or ""):
            raise NotAuthenticatedError("Email o contraseña incorrectos.")

        if user.status != UserStatus.ACTIVE:
            raise ForbiddenError("Esta cuenta no está activa. Contactá al administrador.")

        return user

    def refresh_session(self, refresh_token: str | None) -> User:
        """Valida un refresh token y **lo revoca** (rotación): a partir de acá
        ya no sirve, así que el caller debe emitir un par access+refresh nuevo
        (con ``issue_tokens`` en la capa de API) para no dejar al usuario sin
        sesión.

        Si el mismo token se usa una segunda vez (porque alguien lo copió, o
        por un reintento de red), esta segunda llamada lo encuentra ya
        revocado y falla igual que un token inválido — no se distingue el
        motivo en el mensaje.

        :raises NotAuthenticatedError: token ausente, con firma inválida,
            expirado, de tipo distinto a ``refresh``, ya usado, o de un
            usuario que ya no existe / no está ``ACTIVE``.
        """
        if not refresh_token:
            raise NotAuthenticatedError(_SESSION_INVALID_MESSAGE)

        try:
            payload = decode_token(refresh_token, expected_type="refresh")
        except TokenError as exc:
            raise NotAuthenticatedError(_SESSION_INVALID_MESSAGE) from exc

        jti = payload["jti"]
        if self.tokens.is_revoked(jti):
            raise NotAuthenticatedError(_SESSION_INVALID_MESSAGE)

        user = self.users.get_by_id(int(payload["sub"]))
        if user is None or user.status != UserStatus.ACTIVE:
            raise NotAuthenticatedError(_SESSION_INVALID_MESSAGE)

        expires_at = datetime.fromtimestamp(payload["exp"], tz=UTC)
        self.tokens.revoke(jti, expires_at=expires_at)

        return user

    def logout(self, refresh_token: str | None) -> None:
        """Revoca el refresh token actual (si lo hay y es válido).

        **Nunca lanza.** Cerrar sesión tiene que funcionar aunque la cookie
        esté ausente, vencida o corrupta: para el cliente el resultado es el
        mismo en todos los casos (queda deslogueado). El borrado de la
        cookie en el navegador lo hace la capa de API, no este método.
        """
        if not refresh_token:
            return
        try:
            payload = decode_token(refresh_token, expected_type="refresh")
        except TokenError:
            return

        expires_at = datetime.fromtimestamp(payload["exp"], tz=UTC)
        self.tokens.revoke(payload["jti"], expires_at=expires_at)

    def request_password_reset(self, email: str) -> str | None:
        """Genera un token de reseteo si `email` corresponde a una cuenta
        **local activa** (no aplica a cuentas solo-Google, que no tienen
        contraseña que resetear).

        Devuelve el token en texto plano o ``None`` — la decisión de qué
        hacer con eso (loguearlo en consola en dev, mandarlo por mail en
        producción) es de la capa de API. **Nunca lanza**: el endpoint
        siempre responde 200 sin importar el resultado, para no revelar si
        el email existe.
        """
        clean_email = user_service.normalize_email(email)
        user = self.users.get_by_email(clean_email)
        if user is None or user.status != UserStatus.ACTIVE or user.password_hash is None:
            return None
        token, _jti = create_password_reset_token(user.id)
        return token

    def reset_password(self, token: str, new_password: str) -> None:
        """Cambia la contraseña con un token de `request_password_reset` sin
        usar. Revoca el token al aplicarlo (uso único: uno ya usado no sirve
        una segunda vez).

        A diferencia de los tokens de sesión, acá un token ausente, vencido,
        inválido o ya usado es **400** (dato de entrada incorrecto), no 401
        — no es una sesión que expiró, es un valor de formulario mal
        formado o vencido.

        :raises InvalidInputError: token ausente/inválido/vencido/ya usado,
            de un usuario que ya no existe / no está ``ACTIVE``, o
            `new_password` no cumple el formato.
        """
        if not token:
            raise InvalidInputError(
                "El link de recuperación no es válido.", details={"field": "token"}
            )
        try:
            payload = decode_token(token, expected_type="password_reset")
        except TokenError as exc:
            raise InvalidInputError(
                "El link de recuperación no es válido o venció.", details={"field": "token"}
            ) from exc

        jti = payload["jti"]
        if self.tokens.is_revoked(jti):
            raise InvalidInputError(
                "El link de recuperación ya fue usado.", details={"field": "token"}
            )

        user = self.users.get_by_id(int(payload["sub"]))
        if user is None or user.status != UserStatus.ACTIVE:
            raise InvalidInputError(
                "El link de recuperación no es válido.", details={"field": "token"}
            )

        user_service.validate_password(new_password)

        user.password_hash = hash_password(new_password)
        expires_at = datetime.fromtimestamp(payload["exp"], tz=UTC)
        self.tokens.revoke(jti, expires_at=expires_at)
        self.session.flush()


__all__ = ["AuthService"]
