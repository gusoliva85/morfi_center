import sqlite3

import pytest
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine

from alembic import command
from app.core.config import settings
from app.db.base import Base

EXPECTED_TABLES = {
    "users",
    "user_auth_providers",
    "user_profiles",
    "carts",
    "customer_balances",
}


@pytest.fixture()
def migrated_db(tmp_path, monkeypatch):
    """Base SQLite nueva y vacía, llevada a head con las migraciones reales.

    Se parchea `settings.database_url` y no la URL del Config: `alembic/env.py`
    pisa la URL del Config con la de Settings en cada corrida, así que sin esto
    las migraciones del test irían contra la base de desarrollo real.
    """
    db_path = tmp_path / "test_migrations.db"
    url = f"sqlite:///{db_path}"
    monkeypatch.setattr(settings, "database_url", url)

    command.upgrade(Config("alembic.ini"), "head")
    return url, db_path


def table_names(db_path) -> set[str]:
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        return {row[0] for row in rows}


def test_upgrade_head_creates_every_phase1_table(migrated_db):
    _, db_path = migrated_db
    assert EXPECTED_TABLES <= table_names(db_path)


def test_migrated_schema_matches_the_models(migrated_db):
    """Si alguien toca un modelo y se olvida de generar la migración, esto falla."""
    url, _ = migrated_db
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            diff = compare_metadata(context, Base.metadata)
    finally:
        engine.dispose()

    assert diff == [], f"El esquema migrado no coincide con los modelos: {diff}"


def test_downgrade_removes_every_phase1_table(migrated_db):
    _, db_path = migrated_db
    assert EXPECTED_TABLES <= table_names(db_path)  # precondición: estaban antes

    command.downgrade(Config("alembic.ini"), "-1")

    assert table_names(db_path) & EXPECTED_TABLES == set()


def test_check_constraints_survive_the_migration(migrated_db):
    _, db_path = migrated_db
    with sqlite3.connect(db_path) as conn:
        ddl = " ".join(
            row[0]
            for row in conn.execute("SELECT sql FROM sqlite_master WHERE type = 'table'")
            if row[0]
        )

    assert "CHECK (role IN ('CUSTOMER', 'ADMIN', 'DELIVERY'))" in ddl
    assert "CHECK (balance >= 0)" in ddl
    assert "vehicle_type IN ('moto','bici','auto','a_pie')" in ddl
