import logging

from sqlalchemy.orm import Session

from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


def run_seed(session: Session) -> None:
    """Datos semilla idempotentes (correr dos veces no duplica nada).

    Todavía vacío: se va completando fase a fase (system_settings en
    Fase 2, catálogo demo en Fase 3, usuarios de prueba en Fase 1, etc.).
    """


def main() -> None:
    session = SessionLocal()
    try:
        run_seed(session)
        session.commit()
        logger.info("Seed ejecutado correctamente.")
    finally:
        session.close()


if __name__ == "__main__":
    main()
