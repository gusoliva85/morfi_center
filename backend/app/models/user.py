from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import AuthProvider, DriverStatus, Role, UserStatus
from app.core.timezone import now_utc
from app.db.base import Base
from app.db.types import TimestampMixin, UTCDateTime, enum_column


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    first_name: Mapped[str] = mapped_column(String, nullable=False)
    last_name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    phone: Mapped[str | None] = mapped_column(String)
    password_hash: Mapped[str | None] = mapped_column(String)
    role: Mapped[Role] = mapped_column(
        enum_column(Role, "role"), nullable=False, default=Role.CUSTOMER, index=True
    )
    status: Mapped[UserStatus] = mapped_column(
        enum_column(UserStatus, "status"), nullable=False, default=UserStatus.ACTIVE
    )

    auth_providers: Mapped[list["UserAuthProvider"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    profile: Mapped["UserProfile | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True, uselist=False
    )


class UserAuthProvider(Base):
    __tablename__ = "user_auth_providers"
    __table_args__ = (UniqueConstraint("provider", "provider_uid"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[AuthProvider] = mapped_column(
        enum_column(AuthProvider, "provider"), nullable=False
    )
    provider_uid: Mapped[str | None] = mapped_column(String)
    linked_at: Mapped[datetime] = mapped_column(UTCDateTime, default=now_utc, nullable=False)

    user: Mapped[User] = relationship(back_populates="auth_providers")


class UserProfile(Base):
    __tablename__ = "user_profiles"
    __table_args__ = (
        CheckConstraint(
            "vehicle_type IN ('moto','bici','auto','a_pie') OR vehicle_type IS NULL",
            name="vehicle_type",
        ),
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    vehicle_type: Mapped[str | None] = mapped_column(String)
    capacity: Mapped[int | None] = mapped_column(Integer)
    driver_status: Mapped[DriverStatus | None] = mapped_column(
        enum_column(DriverStatus, "driver_status")
    )
    notes: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=now_utc, onupdate=now_utc, nullable=False
    )

    user: Mapped[User] = relationship(back_populates="profile")
