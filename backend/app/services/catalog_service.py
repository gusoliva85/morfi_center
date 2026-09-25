"""Reglas del catálogo, sin base de datos ni API (lógica pura, igual que
`user_service.py`): los repositorios y los servicios con sesión se apoyan en
esto, no al revés — por eso este módulo no importa nada de `repositories/`.
"""

import re
import unicodedata
from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass

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


# ---------- productos ----------

PRODUCT_NAME_MAX = 80
PRODUCT_DESCRIPTION_MAX = 500
# Tope de cordura, en centavos ($1.000.000): no es una regla de negocio sino una
# red contra un cero de más al tipear un precio (un plato de $10.000 cargado
# como $10.000.000 pasaría en silencio).
MAX_PRICE_CENTS = 100_000_000

_PRODUCT_FIELDS = ("name", "category_id", "base_price", "description", "is_active")


@dataclass(frozen=True)
class ProductData:
    """Un producto ya validado y normalizado, listo para guardar."""

    name: str
    category_id: int
    base_price: int  # centavos
    description: str | None = None
    is_active: bool = True


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)  # True "es" un 1 en Python


def validate_product_name(name: str | None) -> str:
    """Requerido, hasta 80 caracteres y con al menos una letra o un número
    (mismas ideas que el nombre de categoría, con un tope más generoso)."""
    if not isinstance(name, str):
        raise _invalid("name", "El nombre es obligatorio.")
    normalized = normalize_category_name(name)  # recorta y colapsa espacios
    if not normalized:
        raise _invalid("name", "El nombre es obligatorio.")
    if len(normalized) > PRODUCT_NAME_MAX:
        raise _invalid("name", f"El nombre puede tener hasta {PRODUCT_NAME_MAX} caracteres.")
    if not any(char.isalnum() for char in normalized):
        raise _invalid("name", "El nombre tiene que incluir al menos una letra o un número.")
    return normalized


def validate_base_price(price: object) -> int:
    """El precio base en **centavos**: un entero mayor que cero y con tope.

    Nada de flotantes ni de texto (`"100"`, `10.5`): el dinero del sistema son
    enteros, y aceptar un `float` traería errores de redondeo. Tampoco `True`.
    """
    if not _is_int(price):
        raise _invalid("base_price", "El precio tiene que ser un número entero, en centavos.")
    if price <= 0:
        raise _invalid("base_price", "El precio tiene que ser mayor que cero.")
    if price > MAX_PRICE_CENTS:
        raise _invalid(
            "base_price",
            f"El precio no puede superar {MAX_PRICE_CENTS // 100:,} pesos.".replace(",", "."),
        )
    return price


def validate_description(description: str | None) -> str | None:
    """Opcional. Vacía o solo espacios equivale a "sin descripción" (`None`);
    se recortan los extremos pero se respetan los saltos de línea internos."""
    if description is None:
        return None
    if not isinstance(description, str):
        raise _invalid("description", "La descripción tiene que ser un texto.")
    stripped = description.strip()
    if not stripped:
        return None
    if len(stripped) > PRODUCT_DESCRIPTION_MAX:
        raise _invalid(
            "description",
            f"La descripción puede tener hasta {PRODUCT_DESCRIPTION_MAX} caracteres.",
        )
    return stripped


def validate_category_reference(category_id: object, existing_ids: Collection[int]) -> int:
    """La categoría del producto tiene que existir. Se pide la colección de ids
    existentes (en vez de consultar una base) para que esto siga siendo lógica
    pura. Una categoría **inactiva** sí vale: sus productos existen, solo que no
    se muestran mientras esté oculta."""
    if not _is_int(category_id) or category_id not in existing_ids:
        raise _invalid("category_id", "La categoría no existe.")
    return category_id


def validate_is_active(value: object) -> bool:
    if not isinstance(value, bool):
        raise _invalid("is_active", "Tiene que ser verdadero o falso.")
    return value


def _run_validators(checks: dict[str, Callable[[], object]]) -> dict[str, object]:
    """Corre todas las validaciones y, si alguna falla, lanza **un solo** error
    con todos los campos que fallaron (un formulario los muestra juntos, en vez
    de obligar a corregirlos de a uno por intento)."""
    values: dict[str, object] = {}
    problems: list[dict[str, str]] = []
    for field, check in checks.items():
        try:
            values[field] = check()
        except DomainValidationError as exc:
            problems.extend(exc.details["fields"])
    if problems:
        raise DomainValidationError(
            "Hay datos del producto que no son válidos.", {"fields": problems}
        )
    return values


def validate_new_product(
    data: Mapping[str, object], existing_category_ids: Collection[int]
) -> ProductData:
    """Reglas para dar de alta un producto: nombre, categoría existente, precio
    en centavos mayor que cero, descripción opcional. Nace activo salvo que se
    diga lo contrario."""
    values = _run_validators(
        {
            "name": lambda: validate_product_name(data.get("name")),
            "category_id": lambda: validate_category_reference(
                data.get("category_id"), existing_category_ids
            ),
            "base_price": lambda: validate_base_price(data.get("base_price")),
            "description": lambda: validate_description(data.get("description")),
            "is_active": lambda: validate_is_active(data.get("is_active", True)),
        }
    )
    return ProductData(**values)


def validate_product_changes(
    changes: Mapping[str, object], existing_category_ids: Collection[int]
) -> dict[str, object]:
    """Reglas para editar un producto (semántica de PATCH): valida **solo** los
    campos que vienen y devuelve esos mismos, ya normalizados.

    Un campo enviado como `None` es un error salvo `description`, donde `None`
    significa "borrar la descripción". Un campo que no se puede editar da error
    en vez de ignorarse en silencio.
    """
    validators: dict[str, Callable[[object], object]] = {
        "name": validate_product_name,
        "category_id": lambda value: validate_category_reference(value, existing_category_ids),
        "base_price": validate_base_price,
        "description": validate_description,
        "is_active": validate_is_active,
    }
    checks = {}
    for field, value in changes.items():
        if field not in validators:
            raise _invalid(field, "Este campo no se puede modificar.")
        checks[field] = lambda field=field, value=value: validators[field](value)
    return _run_validators(checks)


def search_key(text: str | None) -> str:
    """Forma de un texto para comparar en búsquedas: sin acentos, en minúsculas
    y con los espacios colapsados. "  Sándwich  DE Milanesa " -> "sandwich de milanesa".

    Así buscar "sandwich" encuentra "Sándwich" (y al revés), sin que quien busca
    tenga que acordarse de las tildes."""
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFKD", text)
    without_marks = "".join(char for char in decomposed if not unicodedata.combining(char))
    return _SPACES_RE.sub(" ", without_marks.casefold()).strip()
