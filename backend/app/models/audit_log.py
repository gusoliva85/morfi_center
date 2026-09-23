from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.timezone import now_utc
from app.db.base import Base
from app.db.types import UTCDateTime


class AuditLog(Base):
    """Rastro de acciones sensibles (§6.10 y §20.3): quién hizo qué, sobre qué,
    y con qué valores antes y después.

    `actor_id` puede ser NULL (acciones del sistema) y no se borra en cascada:
    si alguna vez se borra un usuario, su rastro tiene que sobrevivir, porque el
    sentido de auditar es poder revisar el pasado.
    """

    __tablename__ = "audit_log"
    __table_args__ = (Index("ix_audit_entity", "entity_type", "entity_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String, nullable=False)
    entity_type: Mapped[str] = mapped_column(String, nullable=False)
    entity_id: Mapped[str] = mapped_column(String, nullable=False)
    data: Mapped[str | None] = mapped_column(Text)  # JSON con before/after
    ip: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=now_utc, nullable=False)
