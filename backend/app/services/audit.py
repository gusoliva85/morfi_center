import json
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog, User


def record_audit(
    session: Session,
    *,
    actor: User | None,
    action: str,
    entity_type: str,
    entity_id: int | str,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    ip: str | None = None,
) -> AuditLog:
    """Deja una entrada en `audit_log` (§20.3): quién hizo qué, sobre qué y con
    qué valores antes y después. `before`/`after` llevan solo los campos que
    cambiaron. No hace `flush`: viaja en la misma transacción que el cambio que
    describe, así que ambos se guardan o se descartan juntos."""
    data = {
        key: value for key, value in (("before", before), ("after", after)) if value is not None
    }
    entry = AuditLog(
        actor_id=actor.id if actor else None,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        data=json.dumps(data, ensure_ascii=False),
        ip=ip,
    )
    session.add(entry)
    return entry
