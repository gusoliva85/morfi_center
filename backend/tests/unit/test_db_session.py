"""Engine SQLite: PRAGMAs, creación de carpeta y semántica de sesión
(`documentacion/02_Documento_Tecnico.md` §5.2)."""

from pathlib import Path

from sqlalchemy import text

from app.db.session import build_engine, get_session, session_scope


def test_sqlite_pragmas_are_applied(tmp_path: Path):
    engine = build_engine(f"sqlite:///{(tmp_path / 'x.db').as_posix()}")
    with engine.connect() as conn:
        assert conn.execute(text("PRAGMA foreign_keys")).scalar() == 1
        assert conn.execute(text("PRAGMA journal_mode")).scalar() == "wal"
        assert conn.execute(text("PRAGMA busy_timeout")).scalar() == 5000


def test_missing_data_dir_is_created(tmp_path: Path):
    db_file = tmp_path / "nested" / "deep" / "morfi.db"
    build_engine(f"sqlite:///{db_file.as_posix()}")
    assert db_file.parent.is_dir()


def test_session_scope_commits_on_success():
    with session_scope() as db:
        assert db.execute(text("SELECT 1")).scalar() == 1
    assert not db.in_transaction()  # sesión cerrada / sin transacción abierta


def test_session_scope_rolls_back_on_error():
    class Boom(Exception):
        pass

    try:
        with session_scope() as db:
            db.execute(text("SELECT 1"))
            raise Boom
    except Boom:
        pass
    assert not db.in_transaction()


def test_get_session_yields_a_working_session():
    gen = get_session()
    db = next(gen)
    try:
        assert db.execute(text("SELECT 1")).scalar() == 1
    finally:
        gen.close()  # dispara commit + close del context manager interno
