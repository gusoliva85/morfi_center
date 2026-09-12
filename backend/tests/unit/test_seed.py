from app.db.seed import run_seed
from app.db.session import SessionLocal


def test_run_seed_does_not_raise():
    session = SessionLocal()
    try:
        run_seed(session)
    finally:
        session.close()


def test_run_seed_is_idempotent_when_called_twice():
    session = SessionLocal()
    try:
        run_seed(session)
        run_seed(session)  # correr dos veces no debe romper ni duplicar nada
    finally:
        session.close()
