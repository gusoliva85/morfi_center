import pytest
from sqlalchemy import text

from app.db.session import SessionLocal, get_session


def test_foreign_keys_pragma_is_on():
    session = SessionLocal()
    try:
        result = session.execute(text("PRAGMA foreign_keys")).scalar()
        assert result == 1
    finally:
        session.close()


def test_busy_timeout_pragma_is_set():
    session = SessionLocal()
    try:
        result = session.execute(text("PRAGMA busy_timeout")).scalar()
        assert result == 5000
    finally:
        session.close()


def test_get_session_yields_a_working_session_and_commits():
    gen = get_session()
    session = next(gen)
    assert session.execute(text("SELECT 1")).scalar() == 1
    with pytest.raises(StopIteration):
        next(gen)  # agota el generador -> corre el commit + close


def test_get_session_rolls_back_and_reraises_on_exception():
    gen = get_session()
    next(gen)
    with pytest.raises(RuntimeError):
        gen.throw(RuntimeError("boom"))
