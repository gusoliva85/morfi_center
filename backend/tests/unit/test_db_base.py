from sqlalchemy.orm import DeclarativeBase

from app.db.base import NAMING_CONVENTION, Base


def test_base_imports_without_error():
    assert Base is not None
    assert issubclass(Base, DeclarativeBase)


def test_base_metadata_uses_the_naming_convention():
    assert Base.metadata.naming_convention == NAMING_CONVENTION
