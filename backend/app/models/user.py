"""Modelos de identidad: usuarios, proveedores de autenticación y perfil.

Ver ``documentacion/02_Documento_Tecnico.md`` §6.1.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import AuthProvider, DriverStatus, Role, UserStatus, VehicleType
from app.core.timezone import now_utc
from app.db.base import Base, TimestampMixin
from app.db.types import UtcDateTime, sa_enum

if TYPE_CHECKING:
    from app.models.balance import CustomerBalance
    from app.models.cart import Cart


class User(Base, TimestampMixin):
    """Usuario de la plataforma. Un único registro por persona, cualquiera sea
    su rol o método de login (``role`` determina la experiencia; el/los
    proveedores de auth están en ``UserAuthProvider``)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    last_name: Mapped[str] = mapped_column(String(80), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(30))
    # NULL si el usuario solo se autentica por un proveedor externo (Google).
    password_hash: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(
        sa_enum(Role), nullable=False, default=Role.CUSTOMER, index=True
    )
    status: Mapped[UserStatus] = mapped_column(
        sa_enum(UserStatus), nullable=False, default=UserStatus.ACTIVE
    )

    auth_providers: Mapped[list[UserAuthProvider]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    profile: Mapped[UserProfile | None] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    # Se crean junto con el usuario CUSTOMER en AuthService.register (Tema 1.3);
    # acá solo el modelo y la relación (Fase 6 y 12 les suman su lógica propia).
    cart: Mapped[Cart | None] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    balance: Mapped[CustomerBalance | None] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )

    def __repr__(self) -> str:  # pragma: no cover - solo para debugging
        return f"User(id={self.id!r}, email={self.email!r}, role={self.role!r})"


class UserAuthProvider(Base):
    """Vincula un usuario con un método de login (``local`` o ``google``).

    Un usuario puede tener varios (alta local + login con Google vinculado
    luego por el mismo email).
    """

    __tablename__ = "user_auth_providers"
    __table_args__ = (UniqueConstraint("provider", "provider_uid"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[AuthProvider] = mapped_column(sa_enum(AuthProvider), nullable=False)
    # 'sub' de Google para provider='google'; NULL para 'local'.
    provider_uid: Mapped[str | None] = mapped_column(String(255))
    linked_at: Mapped[datetime] = mapped_column(UtcDateTime, default=now_utc, nullable=False)

    user: Mapped[User] = relationship(back_populates="auth_providers")

    def __repr__(self) -> str:  # pragma: no cover
        return f"UserAuthProvider(user_id={self.user_id!r}, provider={self.provider!r})"


class UserProfile(Base):
    """Perfil extendido, unificado para no crear una tabla casi vacía por rol.

    Hoy solo tiene los campos de repartidor (Fase 14); es el lugar natural
    para sumar más adelante lo específico de otros roles.
    """

    __tablename__ = "user_profiles"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    # --- Repartidor ---
    vehicle_type: Mapped[VehicleType | None] = mapped_column(sa_enum(VehicleType))
    capacity: Mapped[int | None] = mapped_column(Integer)
    driver_status: Mapped[DriverStatus | None] = mapped_column(sa_enum(DriverStatus))
    # --- Notas administrativas (cualquier rol) ---
    notes: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime, default=now_utc, onupdate=now_utc, nullable=False
    )

    user: Mapped[User] = relationship(back_populates="profile")

    def __repr__(self) -> str:  # pragma: no cover
        return f"UserProfile(user_id={self.user_id!r}, driver_status={self.driver_status!r})"


__all__ = ["User", "UserAuthProvider", "UserProfile"]
