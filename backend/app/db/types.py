"""Tipos de columna a medida.

``UtcDateTime`` guarda los ``datetime`` como **texto ISO-8601 UTC** (``...Z``) —
tal como pide ``documentacion/02_Documento_Tecnico.md`` §6 — y los devuelve como
``datetime`` *aware* en UTC. El formato ISO-8601 UTC ordena lexicográficamente
igual que cronológicamente, así que los índices y ``ORDER BY`` funcionan sobre el
texto.

``sa_enum`` envuelve los ``StrEnum`` de ``app.core.enums`` para que SQLAlchemy
los persista como ``TEXT`` + ``CHECK`` (no como ``ENUM`` nativo, que SQLite no
tiene) guardando el **valor** del enum, no su nombre de miembro.
"""

from __future__ import annotations

import datetime as _dt
from enum import Enum
from typing import Any, TypeVar

from sqlalchemy import Enum as SAEnum
from sqlalchemy import String
from sqlalchemy.types import TypeDecorator

from app.core.timezone import isoformat_utc, to_utc


class UtcDateTime(TypeDecorator):
    """``datetime`` aware (UTC) persistido como ``TEXT`` ISO-8601 con sufijo ``Z``."""

    impl = String(32)
    cache_ok = True

    def process_bind_param(self, value: _dt.datetime | None, dialect: object) -> str | None:
        if value is None:
            return None
        if not isinstance(value, _dt.datetime):
            raise TypeError(f"UtcDateTime espera datetime, recibió {type(value).__name__!r}")
        if value.tzinfo is None:
            raise ValueError(
                "UtcDateTime requiere un datetime aware (usá core.timezone.now_utc())."
            )
        return isoformat_utc(value)

    def process_result_value(self, value: str | None, dialect: object) -> _dt.datetime | None:
        if value is None:
            return None
        return to_utc(_dt.datetime.fromisoformat(value.replace("Z", "+00:00")))


_E = TypeVar("_E", bound=Enum)


def sa_enum(enum_cls: type[_E], **kwargs: Any) -> SAEnum:
    """``Enum(enum_cls)`` configurado para el estilo del proyecto:

    - ``native_enum=False``: en SQLite se guarda como ``TEXT`` + ``CHECK``
      (coincide con las tablas de ``02_Documento_Tecnico.md`` §6).
    - ``values_callable``: persiste ``member.value`` (p. ej. ``"a_pie"``), no
      ``member.name`` (``"A_PIE"``), que es el default de SQLAlchemy.
    """

    def _values(cls: type[_E]) -> list[str]:
        return [member.value for member in cls]

    kwargs.setdefault("native_enum", False)
    # SQLAlchemy 2.0 dejó de generar el CHECK por defecto para Enum no nativo;
    # lo pedimos explícito porque el modelo de datos del proyecto cuenta con él.
    kwargs.setdefault("create_constraint", True)
    kwargs.setdefault("validate_strings", True)
    kwargs.setdefault("values_callable", _values)
    kwargs.setdefault("length", 32)
    return SAEnum(enum_cls, **kwargs)


__all__ = ["UtcDateTime", "sa_enum"]
