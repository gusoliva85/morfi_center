"""`AuditLogRepository` (`03_Roadmap.md` T-1.7.2)."""

import json

from sqlalchemy import select

from app.core.enums import Role, UserStatus
from app.models.audit import AuditLog
from app.models.user import User
from app.repositories.audit_repository import AuditLogRepository


def _repo(session) -> AuditLogRepository:
    return AuditLogRepository(session)


def _make_actor(session) -> User:
    user = User(
        first_name="Root",
        last_name="Admin",
        email="admin@morficenter.test",
        role=Role.ADMIN,
        status=UserStatus.ACTIVE,
    )
    session.add(user)
    session.flush()
    return user


def test_record_persists_all_fields(session):
    actor = _make_actor(session)
    entry = _repo(session).record(
        actor_id=actor.id,
        action="user.update_role_status",
        entity_type="user",
        entity_id="42",
        data={"before": {"role": "CUSTOMER"}, "after": {"role": "ADMIN"}},
        ip="127.0.0.1",
    )

    assert entry.id is not None
    assert entry.actor_id == actor.id
    assert entry.action == "user.update_role_status"
    assert entry.entity_type == "user"
    assert entry.entity_id == "42"
    assert entry.ip == "127.0.0.1"
    assert entry.created_at is not None
    assert json.loads(entry.data) == {
        "before": {"role": "CUSTOMER"},
        "after": {"role": "ADMIN"},
    }


def test_record_without_data_or_ip_stores_none(session):
    entry = _repo(session).record(
        actor_id=None, action="system.seed", entity_type="user", entity_id="1"
    )
    assert entry.data is None
    assert entry.ip is None
    assert entry.actor_id is None  # NULL = acción del sistema


def test_record_persists_to_the_session(session):
    _repo(session).record(actor_id=None, action="a", entity_type="user", entity_id="1")
    rows = list(session.scalars(select(AuditLog)))
    assert len(rows) == 1
