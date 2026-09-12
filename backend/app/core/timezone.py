"""Utilidades de fecha y hora.

Regla del proyecto (``documentacion/02_Documento_Tecnico.md`` §26):

- Todo instante absoluto se **guarda y compara en UTC** (aware).
- La **zona de operación** es ``settings.app_timezone``
  (``America/Argentina/Buenos_Aires`` por defecto).
- Los horarios del turno (``open_time`` / ``close_time``) son **hora de pared
  local** (``"12:00"``); para una fecha concreta se resuelven a un instante UTC
  con :func:`resolve_shift_instant`.
"""

from __future__ import annotations

import datetime as _dt
from functools import lru_cache
from zoneinfo import ZoneInfo

from app.core.config import settings


@lru_cache(maxsize=8)
def _zone(name: str) -> ZoneInfo:
    return ZoneInfo(name)


def get_tz() -> ZoneInfo:
    """Zona horaria de operación (según ``APP_TIMEZONE``)."""
    return _zone(settings.app_timezone)


def now_utc() -> _dt.datetime:
    """Instante actual, timezone-aware en UTC."""
    return _dt.datetime.now(_dt.UTC)


def to_utc(value: _dt.datetime) -> _dt.datetime:
    """Devuelve ``value`` en UTC (aware).

    Un ``datetime`` naive se interpreta como hora local de operación.
    """
    if value.tzinfo is None:
        value = value.replace(tzinfo=get_tz())
    return value.astimezone(_dt.UTC)


def to_local(value: _dt.datetime) -> _dt.datetime:
    """Devuelve ``value`` en la zona de operación (aware).

    Un ``datetime`` naive se interpreta como UTC.
    """
    if value.tzinfo is None:
        value = value.replace(tzinfo=_dt.UTC)
    return value.astimezone(get_tz())


def parse_hhmm(value: str) -> _dt.time:
    """``"HH:MM"`` (o ``"H:MM"``) -> :class:`datetime.time`.

    Lanza ``ValueError`` si el formato o el rango no son válidos.
    """
    parts = value.strip().split(":")
    if len(parts) != 2 or not all(p.isdigit() for p in parts):
        raise ValueError(f"Hora inválida: {value!r} (se espera 'HH:MM').")
    hour, minute = int(parts[0]), int(parts[1])
    return _dt.time(hour=hour, minute=minute)  # ValueError si fuera de rango


def resolve_shift_instant(service_date: _dt.date | str, hhmm: str) -> _dt.datetime:
    """Instante UTC (aware) que corresponde a ``hhmm`` hora local del día
    ``service_date`` en la zona de operación.

    ``service_date`` puede ser un :class:`datetime.date` o ``"YYYY-MM-DD"``.
    Se resuelve literalmente sobre ese día (el manejo de turnos que cruzan la
    medianoche es responsabilidad de ``ShiftService``).
    """
    if isinstance(service_date, _dt.datetime):
        day = service_date.date()
    elif isinstance(service_date, _dt.date):
        day = service_date
    else:
        day = _dt.date.fromisoformat(service_date)

    t = parse_hhmm(hhmm)
    local_dt = _dt.datetime(day.year, day.month, day.day, t.hour, t.minute, tzinfo=get_tz())
    return local_dt.astimezone(_dt.UTC)


def isoformat_utc(value: _dt.datetime) -> str:
    """Serializa a ISO-8601 en UTC con sufijo ``Z`` (formato de almacenamiento)."""
    return to_utc(value).isoformat().replace("+00:00", "Z")


__all__ = [
    "get_tz",
    "now_utc",
    "to_utc",
    "to_local",
    "parse_hhmm",
    "resolve_shift_instant",
    "isoformat_utc",
]
