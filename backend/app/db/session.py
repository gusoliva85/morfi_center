"""Engine y sesiones de SQLAlchemy.

- SQLite con ``PRAGMA foreign_keys=ON``, ``journal_mode=WAL`` y ``busy_timeout``.
- ``get_session``: dependencia de FastAPI (commit al terminar bien, rollback ante
  excepción, siempre close).
- ``session_scope``: context manager equivalente para jobs, seed y scripts.

El resto de la app importa desde acá; cambiar de motor (SQLite -> PostgreSQL) es
cambiar ``DATABASE_URL`` (ver ``documentacion/02_Documento_Tecnico.md`` §5.2 y §25).
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, event, make_url
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def _ensure_sqlite_dir(url_database: str | None) -> None:
    """Crea la carpeta del archivo SQLite si hace falta."""
    if url_database and url_database != ":memory:":
        Path(url_database).parent.mkdir(parents=True, exist_ok=True)


def build_engine(url: str, **engine_kwargs: object) -> Engine:
    """Crea un Engine a partir de una URL de conexión.

    Para SQLite agrega ``check_same_thread=False`` y registra el listener de
    PRAGMAs. ``engine_kwargs`` extra se pasan a ``create_engine`` (p. ej.
    ``poolclass=StaticPool`` para la DB en memoria de los tests).
    """
    sa_url = make_url(url)
    is_sqlite = sa_url.get_backend_name() == "sqlite"

    connect_args: dict[str, object] = {}
    if is_sqlite:
        connect_args["check_same_thread"] = False
        _ensure_sqlite_dir(sa_url.database)

    engine = create_engine(url, connect_args=connect_args, pool_pre_ping=True, **engine_kwargs)

    if is_sqlite:

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragmas(dbapi_conn, _connection_record):  # noqa: ANN001
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            # WAL no aplica a la DB en memoria; SQLite lo ignora sin error.
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()

    return engine


# ── Instancias a nivel de aplicación ────────────────────
engine: Engine = build_engine(settings.database_url)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    class_=Session,
)


@contextmanager
def session_scope() -> Iterator[Session]:
    """Sesión transaccional para jobs / seed / scripts."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_session() -> Iterator[Session]:
    """Dependencia de FastAPI: ``db = Depends(get_session)``."""
    with session_scope() as db:
        yield db


__all__ = [
    "engine",
    "SessionLocal",
    "build_engine",
    "session_scope",
    "get_session",
]
