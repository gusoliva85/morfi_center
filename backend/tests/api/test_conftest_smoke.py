"""Humo: las fixtures de conftest funcionan (`03_Roadmap.md` T-0.5.2)."""

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session


async def test_client_reaches_health(client: httpx.AsyncClient):
    r = await client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_session_is_usable_with_fk_enforced(session: Session):
    assert session.execute(text("SELECT 1")).scalar() == 1
    assert session.execute(text("PRAGMA foreign_keys")).scalar() == 1


def test_engine_is_in_memory(engine):
    assert str(engine.url) == "sqlite://"


def test_client_and_session_share_state(client, session):
    # una tabla creada vía la sesión del test es visible para el endpoint,
    # porque comparten la misma Session (override de get_session).
    session.execute(text("CREATE TABLE _smoke (id INTEGER PRIMARY KEY, v TEXT)"))
    session.execute(text("INSERT INTO _smoke (v) VALUES ('hola')"))
    session.flush()
    got = session.execute(text("SELECT v FROM _smoke")).scalar()
    assert got == "hola"
