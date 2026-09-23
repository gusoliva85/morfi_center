import re
from collections.abc import Mapping
from typing import Protocol

# Formato simple e intencionalmente permisivo: local@dominio.tld
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class UserProfileFields(Protocol):
    """Lo único que necesita `update_profile`; no depende del modelo `User`, para
    que este módulo siga siendo lógica pura y testeable sin base de datos."""

    first_name: str
    last_name: str
    phone: str | None


def normalize_email(email: str) -> str:
    """Recorta espacios y pasa a minúsculas (el email es case-insensitive)."""
    return email.strip().lower()


def is_valid_email(email: str) -> bool:
    return bool(_EMAIL_RE.match(email))


def validate_password(password: str) -> bool:
    """Política: 8-72 bytes (72 es el límite duro de bcrypt — sin este tope,
    una contraseña más larga hace explotar hash_password con un ValueError
    en vez de un error de validación), con al menos una letra y un número."""
    if len(password) < 8 or len(password.encode("utf-8")) > 72:
        return False
    has_letter = any(c.isalpha() for c in password)
    has_digit = any(c.isdigit() for c in password)
    return has_letter and has_digit


def is_valid_name(name: str | None) -> bool:
    """Nombre/apellido: requerido, no vacío después de recortar espacios."""
    return bool(name and name.strip())


def update_profile(user: UserProfileFields, changes: Mapping[str, str | None]) -> None:
    """Aplica los cambios de perfil sobre el usuario, en el lugar.

    `changes` trae **solo** los campos que el cliente mandó (semántica de PATCH):
    un campo ausente no se toca, y `phone=None` sí borra el teléfono. Sin esa
    distinción, editar solo el nombre borraría el teléfono sin querer.

    El email y el rol no se tocan acá: cambiar el email es cambiar la identidad
    con la que se entra (necesita su propio flujo con verificación) y el rol solo
    lo cambia un admin (`T-1.7.2`).
    """
    if "first_name" in changes:
        if not is_valid_name(changes["first_name"]):
            raise ValueError("El nombre es requerido.")
        user.first_name = changes["first_name"].strip()

    if "last_name" in changes:
        if not is_valid_name(changes["last_name"]):
            raise ValueError("El apellido es requerido.")
        user.last_name = changes["last_name"].strip()

    if "phone" in changes:
        phone = (changes["phone"] or "").strip()
        user.phone = phone or None  # vacío se guarda como NULL, no como ""
