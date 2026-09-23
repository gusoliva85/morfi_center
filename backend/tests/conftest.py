import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.rate_limit import limiter
from app.db.base import Base
from app.db.session import get_session
from app.main import app


@pytest.fixture(autouse=True)
def reset_rate_limit():
    """El límite de intentos (T-1.4.5) vive en memoria del proceso y todos los
    tests comparten la misma IP: sin resetearlo, un test que hace varios logins
    dejaría a los siguientes con 429."""
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture()
def session():
    """DB SQLite en memoria, aislada por test. StaticPool: una sola conexión
    para todo el engine, si no cada checkout de sqlite:// en memoria abriría
    una base nueva y vacía (se pierde el esquema entre queries)."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_connection, connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


@pytest.fixture()
async def client(session):
    """httpx.AsyncClient contra la app real, con get_session sobreescrito
    para usar la sesión de test en memoria en vez de la base real."""

    def _override_get_session():
        yield session

    app.dependency_overrides[get_session] = _override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.clear()
