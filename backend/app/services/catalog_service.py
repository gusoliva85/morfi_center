"""Reglas del catálogo, sin base de datos ni API (lógica pura, igual que
`user_service.py`): los repositorios y los servicios con sesión se apoyan en
esto, no al revés — por eso este módulo no importa nada de `repositories/`.
"""

import re
import unicodedata
from collections.abc import Collection, Sequence

from app.core.errors import DomainValidationError

CATEGORY_NAME_MAX = 60
FALLBACK_SLUG = "categoria"  # para nombres sin ningún carácter latino (p. ej. "寿司")

_SPACES_RE = re.compile(r"\s+")
_NON_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _invalid(field: str, message: str) -> DomainValidationError:
    """Mismo formato de error que el 422 del resto de la API (`details.fields`)."""
    return DomainValidationError(message, {"fields": [{"field": field, "message": message}]})


def normalize_category_name(name: str) -> str:
    """Recorta y colapsa los espacios: "  Plato   del\tdía " -> "Plato del día".
    Sin esto, dos categorías que se ven iguales podrían ser strings distintos."""
    return _SPACES_RE.sub(" ", name).strip()


def validate_category_name(name: str | None) -> str:
    """Devuelve el nombre normalizado o lanza `DomainValidationError`.

    Requerido, hasta 60 caracteres y con al menos una letra o un número: un
    nombre como "???" no le dice nada al cliente y ni siquiera da un slug.
    """
    normalized = normalize_category_name(name or "")
    if not normalized:
        raise _invalid("name", "El nombre es obligatorio.")
    if len(normalized) > CATEGORY_NAME_MAX:
        raise _invalid("name", f"El nombre puede tener hasta {CATEGORY_NAME_MAX} caracteres.")
    if not any(char.isalnum() for char in normalized):
        raise _invalid("name", "El nombre tiene que incluir al menos una letra o un número.")
    return normalized


def slugify(name: str) -> str:
    """ "Sándwiches" -> "sandwiches", "Empanadas & Más" -> "empanadas-mas".

    Minúsculas, sin acentos (ni la ñ), y todo lo que no sea letra o número pasa
    a un único guion. Un nombre sin ningún carácter latino (que quedaría vacío)
    cae en `categoria`, para que el slug nunca sea un string vacío.
    """
    ascii_only = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    slug = _NON_SLUG_RE.sub("-", ascii_only.lower()).strip("-")
    return slug or FALLBACK_SLUG


def unique_slug(base: str, taken: Collection[str]) -> str:
    """El slug tal cual si está libre; si no, `base-2`, `base-3`, ... hasta el
    primero disponible. `taken` son los slugs que ya existen."""
    if base not in taken:
        return base
    suffix = 2
    while f"{base}-{suffix}" in taken:
        suffix += 1
    return f"{base}-{suffix}"


def build_category_slug(name: str, taken: Collection[str]) -> str:
    """El slug de una categoría nueva: derivado del nombre y único entre `taken`.

    Se calcula **solo al crear**: renombrar una categoría no cambia su slug,
    para no romper los links que ya apunten a ella.
    """
    return unique_slug(slugify(name), taken)


def compute_reorder(current_ids: Collection[int], ordered_ids: Sequence[int]) -> dict[int, int]:
    """El nuevo `sort_order` de cada categoría a partir de la lista de ids en el
    orden deseado: `{id: posición}` con posiciones 0, 1, 2, ...

    `ordered_ids` tiene que ser **exactamente** el conjunto de categorías
    existentes, cada una una sola vez: una lista parcial dejaría a las que
    faltan con un orden ambiguo, y una con ids repetidos o inexistentes es un
    error del cliente que no conviene "arreglar" en silencio.
    """
    if len(set(ordered_ids)) != len(ordered_ids):
        raise _invalid("ids", "La lista tiene categorías repetidas.")

    expected = set(current_ids)
    received = set(ordered_ids)
    if received - expected:
        raise _invalid("ids", "La lista incluye categorías que no existen.")
    if expected - received:
        raise _invalid("ids", "La lista tiene que incluir todas las categorías.")

    return {category_id: position for position, category_id in enumerate(ordered_ids)}
