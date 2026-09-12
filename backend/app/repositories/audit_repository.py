"""Acceso a datos del registro de auditoría (ver `app/models/audit.py`)."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.core.timezone import now_utc
from app.models.audit import AuditLog


class AuditLogRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def record(
        self,
        *,
        actor_id: int | None,
        action: str,
        entity_type: str,
        entity_id: str,
        data: dict[str, Any] | None = None,
        ip: str | None = None,
    ) -> AuditLog:
        """Agrega una entrada de auditoría. `data` se serializa con
        `json.dumps` tal cual — quien llama debe pasar un dict con valores
        simples (ver los usos en `AuthService`)."""
        entry = AuditLog(
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            data=json.dumps(data) if data is not None else None,
            ip=ip,
            created_at=now_utc(),
        )
        self.session.add(entry)
        self.session.flush()
        return entry


__all__ = ["AuditLogRepository"]
