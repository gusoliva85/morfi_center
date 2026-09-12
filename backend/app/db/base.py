from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Convención de nombres de constraints/índices: nombres predecibles y legibles
# en vez de los autogenerados por SQLAlchemy, importante para Alembic (sobre
# todo en SQLite, que usa "batch mode" para ALTER — ver 02_Documento_Tecnico.md §23).
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


# A medida que se creen los modelos (fase a fase, a partir de Fase 1) se
# importan acá para que Base.metadata los conozca y Alembic los detecte
# con --autogenerate. Todavía no hay ninguno.
