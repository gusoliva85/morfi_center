from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import DateTime, TypeDecorator
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.core.timezone import UTC, now_utc


class UTCDateTime(TypeDecorator):
    """SQLite guarda datetimes sin zona horaria: acá se fuerza UTC al escribir
    y se devuelve siempre con tzinfo=UTC al leer (nunca un datetime naive)."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Any) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("UTCDateTime requiere un datetime con zona horaria (tz-aware).")
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect: Any) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=UTC)


def enum_column(enum_cls: type[Enum], name: str) -> SAEnum:
    """Enum de Python guardado como TEXT + CHECK (§6 del Documento Técnico),
    persistiendo el *valor* del enum (no su nombre)."""
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
        values_callable=lambda members: [member.value for member in members],
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=now_utc, onupdate=now_utc, nullable=False
    )
