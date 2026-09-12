"""Base declarativa de SQLAlchemy.

- ``Base``: clase declarativa con una ``MetaData`` que aplica una **convención de
  nombres** a índices y constraints (necesario para que Alembic autogenere
  migraciones estables y para el *batch mode* de SQLite).
- ``TimestampMixin``: agrega ``created_at`` / ``updated_at`` (UTC, ISO-8601).

Los modelos concretos viven en ``app/models/`` y heredan de ``Base``. El módulo
``app.models`` los importa a todos para que ``Base.metadata`` los conozca.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.timezone import now_utc
from app.db.types import UtcDateTime

# Convención recomendada por SQLAlchemy para trabajar con Alembic.
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base declarativa común a todos los modelos."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class TimestampMixin:
    """Columnas de auditoría temporal (UTC, ISO-8601)."""

    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime,
        default=now_utc,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime,
        default=now_utc,
        onupdate=now_utc,
        nullable=False,
    )


__all__ = ["Base", "TimestampMixin", "NAMING_CONVENTION"]
