"""Reglas de validación de usuario (lógica pura: sin FastAPI, sin DB).

Valida la **forma** de los datos de un usuario (email, nombre/apellido,
teléfono, contraseña). La unicidad del email se valida contra el repositorio
en el Tema 1.3 (``AuthService.register``); acá no se toca la base de datos.

Toda función que rechaza un valor lanza :class:`app.core.errors.InvalidInputError`
(400), con ``details.field`` indicando qué campo falló — así el handler global
ya devuelve el formato de error correcto sin lógica extra en la API.
"""

from __future__ import annotations

import re

from app.core.errors import InvalidInputError
from app.models.user import User

# Simple y permisiva a propósito: alcanza con rechazar lo obviamente inválido
# (sin espacios, con un único "@" y al menos un "." en el dominio). La
# verificación real de que la casilla existe no es responsabilidad de esta capa.
_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

# Dígitos con separadores comunes (espacio, guion, paréntesis) y "+" opcional al inicio.
_PHONE_RE = re.compile(r"^[+(]?\d[\d\s()-]{5,19}$")

# Caracteres permitidos en un nombre además de letras (cubre "María José",
# "O'Connor", "Jean-Paul", "D'Angelo Jr."). str.isalpha() ya es Unicode-aware
# (acentos, ñ, etc.), así que no hace falta una regex con rangos de códigos.
_NAME_EXTRA_CHARS = " '-."

MIN_NAME_LENGTH = 2
MAX_NAME_LENGTH = 80
MIN_PASSWORD_LENGTH = 8


def normalize_email(email: str | None) -> str:
    """Recorta espacios, pasa a minúsculas y valida el formato.

    :raises InvalidInputError: si el email está vacío o mal formado.
    """
    value = (email or "").strip().lower()
    if not value or not _EMAIL_RE.match(value):
        raise InvalidInputError("El email no es válido.", details={"field": "email"})
    return value


def validate_person_name(value: str | None, *, field: str = "nombre") -> str:
    """Valida nombre/apellido: requerido, sin dígitos, longitud razonable.

    :raises InvalidInputError: si está vacío o no cumple el formato.
    """
    cleaned = (value or "").strip()
    valid = (
        MIN_NAME_LENGTH <= len(cleaned) <= MAX_NAME_LENGTH
        and any(ch.isalpha() for ch in cleaned)
        and all(ch.isalpha() or ch in _NAME_EXTRA_CHARS for ch in cleaned)
    )
    if not valid:
        raise InvalidInputError(
            f"El campo '{field}' es obligatorio y no puede contener números.",
            details={"field": field},
        )
    return cleaned


def normalize_phone(value: str | None) -> str | None:
    """Teléfono **opcional**: ``None``/vacío se acepta tal cual; si viene con
    contenido, se valida el formato.

    :raises InvalidInputError: si viene un valor no vacío con formato inválido.
    """
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if not _PHONE_RE.match(cleaned):
        raise InvalidInputError("El teléfono no es válido.", details={"field": "phone"})
    return cleaned


def validate_password(password: str | None) -> None:
    """Política de contraseña: mínimo 8 caracteres, al menos una letra y un número.

    No devuelve nada; si la contraseña no cumple, lanza con el detalle de qué
    reglas faltaron (útil para mostrarlas todas juntas en el formulario).

    :raises InvalidInputError: si no cumple alguna regla.
    """
    value = password or ""
    failed: list[str] = []
    if len(value) < MIN_PASSWORD_LENGTH:
        failed.append(f"mínimo {MIN_PASSWORD_LENGTH} caracteres")
    if not any(ch.isalpha() for ch in value):
        failed.append("al menos una letra")
    if not any(ch.isdigit() for ch in value):
        failed.append("al menos un número")

    if failed:
        raise InvalidInputError(
            "La contraseña no cumple los requisitos: " + ", ".join(failed) + ".",
            details={"field": "password", "requirements_failed": failed},
        )


def update_profile(user: User, updates: dict[str, str | None]) -> User:
    """Aplica un PATCH parcial de perfil sobre ``user`` (in-place; el commit
    lo hace ``get_session`` al terminar la request, no esta función).

    Solo toca las claves presentes en ``updates`` — no reenviar un campo lo
    deja como estaba; enviarlo con valor ``None`` (p. ej. ``phone``) lo
    borra. ``email`` no se acepta acá a propósito (cambiarlo implica
    reverificación, fuera del alcance de este endpoint).

    :raises InvalidInputError: si algún valor presente no cumple su formato
        (propagado desde ``validate_person_name`` / ``normalize_phone``).
    """
    if "first_name" in updates:
        user.first_name = validate_person_name(updates["first_name"], field="first_name")
    if "last_name" in updates:
        user.last_name = validate_person_name(updates["last_name"], field="last_name")
    if "phone" in updates:
        user.phone = normalize_phone(updates["phone"])
    return user


__all__ = [
    "MIN_PASSWORD_LENGTH",
    "normalize_email",
    "validate_person_name",
    "normalize_phone",
    "validate_password",
    "update_profile",
]
