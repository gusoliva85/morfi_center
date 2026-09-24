from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import SettingValueType
from app.core.timezone import now_utc
from app.db.base import Base
from app.db.types import UTCDateTime, enum_column


class SystemSetting(Base):
    """Configuración clave/valor (§6.10). `value` siempre guarda JSON válido —
    para un string común eso es `'"algo"'` (con las comillas), para un entero
    `'40'`, etc. `json.loads` decodifica los cuatro casos sin distinción, así
    que `value_type` es metadata informativa (qué esperar antes de leerlo),
    no algo que cambie cómo se guarda o se lee.
    """

    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    value_type: Mapped[SettingValueType] = mapped_column(
        enum_column(SettingValueType, "value_type"),
        nullable=False,
        default=SettingValueType.JSON,
    )
    description: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=now_utc, onupdate=now_utc, nullable=False
    )
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
