"""Acceso a datos de usuarios (``User`` / ``UserAuthProvider``).

Ningún método hace ``commit``: sólo ``flush`` cuando hace falta el ``id``
generado. El commit final es responsabilidad de quien abrió la sesión
(``get_session`` / ``session_scope``), para que el llamador controle la unidad
de trabajo (p. ej. crear el usuario + su carrito + su saldo en una sola
transacción, como hace ``AuthService.register`` en el Tema 1.3).
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import AuthProvider, Role, UserStatus
from app.core.timezone import now_utc
from app.models.user import User, UserAuthProvider
from app.repositories.pagination import Page, clamp_pagination


class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    # ── Lecturas ─────────────────────────────────────────
    def get_by_id(self, user_id: int) -> User | None:
        return self.session.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        """Busca por email **tal como se pasa** (normalizarlo es responsabilidad
        de ``user_service.normalize_email``, no de este repositorio)."""
        stmt = select(User).where(User.email == email)
        return self.session.scalars(stmt).first()

    def list(
        self,
        *,
        role: Role | None = None,
        page: int | None = None,
        page_size: int | None = None,
    ) -> Page[User]:
        """Lista usuarios, opcionalmente filtrados por rol, paginados y
        ordenados por id."""
        page, page_size = clamp_pagination(page, page_size)

        base = select(User)
        if role is not None:
            base = base.where(User.role == role)

        total = self.session.scalar(select(func.count()).select_from(base.subquery())) or 0

        stmt = base.order_by(User.id).offset((page - 1) * page_size).limit(page_size)
        items = list(self.session.scalars(stmt))
        return Page(items=items, page=page, page_size=page_size, total=total)

    def get_provider(self, provider: AuthProvider, provider_uid: str) -> UserAuthProvider | None:
        stmt = select(UserAuthProvider).where(
            UserAuthProvider.provider == provider,
            UserAuthProvider.provider_uid == provider_uid,
        )
        return self.session.scalars(stmt).first()

    # ── Escrituras ───────────────────────────────────────
    def create(
        self,
        *,
        first_name: str,
        last_name: str,
        email: str,
        phone: str | None = None,
        password_hash: str | None = None,
        role: Role = Role.CUSTOMER,
        status: UserStatus = UserStatus.ACTIVE,
    ) -> User:
        """Crea el usuario. No valida forma ni unicidad del email — eso ya
        pasó por ``user_service`` y por el ``get_by_email`` de quien llama."""
        user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            password_hash=password_hash,
            role=role,
            status=status,
        )
        self.session.add(user)
        self.session.flush()
        return user

    def link_provider(
        self,
        user: User,
        provider: AuthProvider,
        provider_uid: str | None = None,
    ) -> UserAuthProvider:
        link = UserAuthProvider(
            user_id=user.id,
            provider=provider,
            provider_uid=provider_uid,
            linked_at=now_utc(),
        )
        self.session.add(link)
        self.session.flush()
        return link


__all__ = ["UserRepository"]
