"""Base declarativa, convención de nombres y tipo ``UtcDateTime``
(`documentacion/02_Documento_Tecnico.md` §6)."""

import datetime as dt

import pytest
from sqlalchemy import MetaData, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
from sqlalchemy.schema import CreateTable

from app.db.base import NAMING_CONVENTION, Base, TimestampMixin
from app.db.session import build_engine
from app.db.types import UtcDateTime


def test_base_imports_and_has_naming_convention():
    assert set(Base.metadata.naming_convention) == {"ix", "uq", "ck", "fk", "pk"}
    assert NAMING_CONVENTION["pk"] == "pk_%(table_name)s"


def test_models_aggregator_reexports_base():
    import app.models

    assert app.models.Base is Base


def test_utc_datetime_bind_and_result_roundtrip():
    col = UtcDateTime()
    aware = dt.datetime(2026, 9, 10, 15, 0, tzinfo=dt.UTC)
    stored = col.process_bind_param(aware, None)
    assert stored == "2026-09-10T15:00:00Z"

    loaded = col.process_result_value(stored, None)
    assert loaded == aware
    assert loaded.tzinfo is dt.UTC


def test_utc_datetime_rejects_naive_and_wrong_type():
    col = UtcDateTime()
    with pytest.raises(ValueError):
        col.process_bind_param(dt.datetime(2026, 9, 10, 12, 0), None)
    with pytest.raises(TypeError):
        col.process_bind_param("2026-09-10", None)
    assert col.process_bind_param(None, None) is None


def test_timestamp_mixin_and_convention_on_a_model():
    # Base local para no ensuciar Base.metadata global.
    local_meta = MetaData(naming_convention=NAMING_CONVENTION)

    class LocalBase(DeclarativeBase):
        metadata = local_meta

    class Thing(LocalBase, TimestampMixin):
        __tablename__ = "thing"
        id: Mapped[int] = mapped_column(primary_key=True)
        code: Mapped[str] = mapped_column(unique=True)

    ddl = str(CreateTable(Thing.__table__))
    assert "pk_thing" in ddl
    assert "uq_thing_code" in ddl

    engine = build_engine("sqlite://")
    local_meta.create_all(engine)
    with Session(engine) as s:
        s.add(Thing(code="abc"))
        s.commit()
        row = s.scalars(select(Thing)).one()
        assert isinstance(row.created_at, dt.datetime)
        assert row.created_at.tzinfo is dt.UTC
        assert row.updated_at.tzinfo is dt.UTC
