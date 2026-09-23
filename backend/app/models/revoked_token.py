from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import UTCDateTime


class RevokedToken(Base):
    """Refresh tokens que ya no sirven, por rotación (`/auth/refresh`) o por
    logout. Se guarda el `jti` del token, no el token entero.

    `expires_at` es el vencimiento del propio token: pasada esa fecha el token
    ya falla por vencido y la fila no aporta nada, así que se puede borrar (ver
    `AuthService._purge_expired_revocations`). Sin esa limpieza la tabla
    crecería para siempre: cada refresh agrega una fila.
    """

    __tablename__ = "revoked_tokens"

    jti: Mapped[str] = mapped_column(String, primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, index=True)
