"""Entorno de Alembic para Morfi Center.

- La URL de conexión sale de ``app.core.config.settings`` (no de ``alembic.ini``).
- ``target_metadata`` es ``Base.metadata`` con TODOS los modelos registrados
  (se importan vía ``app.models``).
- ``render_as_batch=True`` en SQLite para poder alterar tablas.
"""

from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.engine import Connection, create_engine

from alembic import context

# --- Hacer importable el paquete `app` (backend/ en sys.path) ---
_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.core.config import settings  # noqa: E402
from app.db.base import Base  # noqa: E402
import app.models  # noqa: E402, F401  (registra todos los modelos en Base.metadata)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# URL efectiva: la de Settings (DATABASE_URL). Se permite override explícito
# vía `config.set_main_option("sqlalchemy.url", ...)` (útil para tests / one-offs).
_DB_URL = (config.get_main_option("sqlalchemy.url") or "").strip() or settings.database_url
config.set_main_option("sqlalchemy.url", _DB_URL)

target_metadata = Base.metadata

_IS_SQLITE = _DB_URL.startswith("sqlite")


def _configure(**kwargs: object) -> None:
    context.configure(
        target_metadata=target_metadata,
        render_as_batch=_IS_SQLITE,
        compare_type=True,
        compare_server_default=True,
        **kwargs,
    )


def run_migrations_offline() -> None:
    _configure(
        url=_DB_URL,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def _run(connection: Connection) -> None:
    _configure(connection=connection)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(_DB_URL, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        _run(connection)
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
