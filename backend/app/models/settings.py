"""Configuración clave/valor del sistema (`documentacion/02_Documento_Tecnico.md` §6.10).

Cada fila es una clave conocida (`shift.default`, `payment.transfer`, ...) con
su valor serializado en JSON — incluso los valores "simples" (`"string"`,
`42`, `true`) viajan como JSON para no tener que ramificar el parseo por
`value_type`; ese campo es metadata (para validar/mostrar), no un códec
distinto. Las claves y sus defaults viven en `SettingsService` (Tema 2.1).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import SettingValueType
from app.core.timezone import now_utc
from app.db.base import Base
from app.db.types import UtcDateTime, sa_enum


class SystemSetting(Base):
    """Una clave de configuración del sistema."""

    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)  # JSON serializado
    value_type: Mapped[SettingValueType] = mapped_column(
        sa_enum(SettingValueType), nullable=False, default=SettingValueType.JSON
    )
    description: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime, default=now_utc, onupdate=now_utc, nullable=False
    )
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    def __repr__(self) -> str:  # pragma: no cover
        return f"SystemSetting(key={self.key!r}, value_type={self.value_type!r})"


__all__ = ["SystemSetting"]
