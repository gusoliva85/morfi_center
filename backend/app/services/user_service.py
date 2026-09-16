import re

# Formato simple e intencionalmente permisivo: local@dominio.tld
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(email: str) -> str:
    """Recorta espacios y pasa a minúsculas (el email es case-insensitive)."""
    return email.strip().lower()


def is_valid_email(email: str) -> bool:
    return bool(_EMAIL_RE.match(email))


def validate_password(password: str) -> bool:
    """Política mínima: al menos 8 caracteres, con al menos una letra y un número."""
    if len(password) < 8:
        return False
    has_letter = any(c.isalpha() for c in password)
    has_digit = any(c.isdigit() for c in password)
    return has_letter and has_digit


def is_valid_name(name: str | None) -> bool:
    """Nombre/apellido: requerido, no vacío después de recortar espacios."""
    return bool(name and name.strip())
