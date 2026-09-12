"""Registro de auditoría (`documentacion/02_Documento_Tecnico.md` §6.10, §20.3).

Se escribe desde los *services* (no desde la capa de API) para no perder
eventos internos/jobs. Tabla append-only: sin `updated_at`, nunca se edita
una fila ya escrita.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.timezone import now_utc
from app.db.base import Base
from app.db.types import UtcDateTime


class AuditLog(Base):
    """Una entrada de auditoría: quién hizo qué, sobre qué entidad."""

    __tablename__ = "audit_log"
    __table_args__ = (Index("ix_audit_entity", "entity_type", "entity_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    # NULL = acción del sistema (job, seed), no de una persona.
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(80), nullable=False)
    data: Mapped[str | None] = mapped_column(Text)  # JSON: {"before": {...}, "after": {...}}
    ip: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=now_utc, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"AuditLog(action={self.action!r}, entity_type={self.entity_type!r}, entity_id={self.entity_id!r})"


__all__ = ["AuditLog"]
