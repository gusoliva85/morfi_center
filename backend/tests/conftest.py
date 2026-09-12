"""Fixtures compartidas de la suite.

- ``engine``  : Engine SQLite **en memoria**, esquema creado desde ``Base.metadata``
                (una DB nueva por test).
- ``session`` : ``Session`` de SQLAlchemy sobre ese engine (para tests de repos/servicios).
- ``client``  : ``httpx.AsyncClient`` contra la app FastAPI, con ``get_session``
                apuntando a la misma ``session`` del test.
- ``_reset_rate_limiter`` (autouse): el rate limiter de auth (``app.core.rate_limit.limiter``)
  es un singleton de módulo, igual que en producción — sin este reset, el cupo de
  10/min se iría gastando entre tests de archivos distintos y algunos empezarían
  a fallar con 429 sin ningún motivo relacionado a lo que están probando.

`pyproject.toml` ya fija ``asyncio_mode = "auto"``, así que los tests async no
necesitan decorador.
"""

from collections.abc import AsyncIterator, Iterator

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (registra todos los modelos en Base.metadata)
from app.core.rate_limit import limiter
from app.db.base import Base
from app.db.session import build_engine, get_session
from app.main import create_app


@pytest.fixture(autouse=True)
def _reset_rate_limiter() -> None:
    limiter.reset()


@pytest.fixture
def engine() -> Iterator[Engine]:
    eng = build_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(eng)
    try:
        yield eng
    finally:
        Base.metadata.drop_all(eng)
        eng.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    with Session(engine, expire_on_commit=False) as db:
        yield db


@pytest_asyncio.fixture
async def client(engine: Engine, session: Session) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app()
    # el endpoint usa la MISMA sesión que el test (ve datos aunque no se commiteen)
    app.dependency_overrides[get_session] = lambda: session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.clear()
