"""Refresh tokens revocados (rotación en `/auth/refresh` y `/auth/logout`).

No está en `documentacion/02_Documento_Tecnico.md` §6 porque esa versión del
documento resolvía la revocación "o bien con esta tabla, o bien por rotación"
(§13.1); acá se implementan ambas cosas juntas: cada uso de un refresh lo
revoca (rotación) y esta tabla es lo que permite detectar el *reuse* de un
token ya rotado.

No hay job de limpieza todavía (las filas quedan para siempre); es un buen
candidato para una tarea de mantenimiento futura, no bloqueante para el MVP.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.timezone import now_utc
from app.db.base import Base
from app.db.types import UtcDateTime


class RevokedToken(Base):
    """Un `jti` de refresh token que ya no debe aceptarse."""

    __tablename__ = "revoked_tokens"

    jti: Mapped[str] = mapped_column(String(64), primary_key=True)
    # exp original del token: útil para un futuro job de limpieza (borrar los
    # que ya vencerían solos igual).
    expires_at: Mapped[datetime] = mapped_column(UtcDateTime, nullable=False)
    revoked_at: Mapped[datetime] = mapped_column(UtcDateTime, default=now_utc, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"RevokedToken(jti={self.jti!r})"


__all__ = ["RevokedToken"]
