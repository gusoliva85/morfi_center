import pytest

from app.core.errors import DomainValidationError
from app.services.catalog_service import (
    CATEGORY_NAME_MAX,
    FALLBACK_SLUG,
    build_category_slug,
    compute_reorder,
    normalize_category_name,
    slugify,
    unique_slug,
    validate_category_name,
)


def error_field(exc_info) -> str:
    return exc_info.value.details["fields"][0]["field"]


# ---------- nombre ----------


def test_the_name_is_trimmed_and_inner_spaces_collapsed():
    assert normalize_category_name("  Plato   del\tdía \n") == "Plato del día"


def test_a_valid_name_is_returned_normalized():
    assert validate_category_name("  Sándwiches ") == "Sándwiches"


@pytest.mark.parametrize("name", [None, "", "   ", "\t\n"])
def test_a_missing_or_blank_name_is_rejected(name):
    with pytest.raises(DomainValidationError) as exc_info:
        validate_category_name(name)

    assert error_field(exc_info) == "name"
    assert exc_info.value.status_code == 422


def test_the_name_length_limit_is_inclusive():
    assert validate_category_name("a" * CATEGORY_NAME_MAX) == "a" * CATEGORY_NAME_MAX

    with pytest.raises(DomainValidationError):
        validate_category_name("a" * (CATEGORY_NAME_MAX + 1))


def test_the_length_limit_counts_the_normalized_name():
    """Los espacios de sobra no cuentan: no se rechaza por lo que se va a recortar."""
    padded = "  " + "a" * CATEGORY_NAME_MAX + "   "

    assert validate_category_name(padded) == "a" * CATEGORY_NAME_MAX


@pytest.mark.parametrize("name", ["???", "- - -", "¡!"])
def test_a_name_without_letters_or_numbers_is_rejected(name):
    with pytest.raises(DomainValidationError):
        validate_category_name(name)


@pytest.mark.parametrize("name", ["Pizza", "2x1", "Ñoquis", "寿司"])
def test_names_in_any_alphabet_or_with_numbers_are_accepted(name):
    assert validate_category_name(name) == name


# ---------- slug ----------


@pytest.mark.parametrize(
    ("name", "slug"),
    [
        ("Pizza", "pizza"),
        ("Sándwiches", "sandwiches"),
        ("Acompañamientos", "acompanamientos"),
        ("Ñoquis", "noquis"),
        ("Plato del Día", "plato-del-dia"),
        ("  Pastas  ", "pastas"),
        ("Empanadas & Más!", "empanadas-mas"),
        ("Carnes -- y   parrilla", "carnes-y-parrilla"),
        ("2x1 Combos", "2x1-combos"),
        ("¡Ofertas!", "ofertas"),
    ],
)
def test_the_slug_is_derived_from_the_name(name, slug):
    assert slugify(name) == slug


@pytest.mark.parametrize("name", ["寿司", "???", "---"])
def test_a_name_with_no_latin_characters_falls_back_to_a_default_slug(name):
    assert slugify(name) == FALLBACK_SLUG


def test_the_slug_only_has_lowercase_letters_numbers_and_single_hyphens():
    slug = slugify("  ¡Ñandú, Ñoquis & CÍA.!  --  2ª edición ")

    assert slug == slug.lower()
    assert all(char.isalnum() or char == "-" for char in slug)
    assert "--" not in slug
    assert not slug.startswith("-") and not slug.endswith("-")


def test_a_free_slug_is_kept_as_is():
    assert unique_slug("pizza", {"pastas", "empanadas"}) == "pizza"
    assert unique_slug("pizza", set()) == "pizza"


def test_a_taken_slug_gets_the_next_free_number():
    assert unique_slug("pizza", {"pizza"}) == "pizza-2"
    assert unique_slug("pizza", {"pizza", "pizza-2"}) == "pizza-3"
    assert unique_slug("pizza", ["pizza", "pizza-2", "pizza-3", "pizza-4"]) == "pizza-5"


def test_a_gap_in_the_numbers_is_filled_first():
    """Si "pizza-2" se borró pero "pizza" y "pizza-3" siguen, el próximo es "pizza-2"."""
    assert unique_slug("pizza", {"pizza", "pizza-3"}) == "pizza-2"


def test_a_numbered_slug_alone_does_not_block_the_base():
    assert unique_slug("pizza", {"pizza-2"}) == "pizza"


def test_names_that_collide_after_slugifying_get_distinct_slugs():
    """El caso del roadmap: "Sándwiches" y "Sandwiches" dan el mismo slug base."""
    taken: set[str] = set()
    for name in ("Sándwiches", "Sandwiches", "SÁNDWICHES"):
        taken.add(build_category_slug(name, taken))

    assert taken == {"sandwiches", "sandwiches-2", "sandwiches-3"}


def test_the_fallback_slug_also_resolves_collisions():
    taken = {FALLBACK_SLUG}

    assert build_category_slug("寿司", taken) == f"{FALLBACK_SLUG}-2"


# ---------- reordenar ----------


def test_reorder_gives_consecutive_positions_from_zero():
    assert compute_reorder([1, 2, 3], [3, 1, 2]) == {3: 0, 1: 1, 2: 2}


def test_reorder_with_the_same_order_is_the_identity():
    assert compute_reorder([5, 7, 9], [5, 7, 9]) == {5: 0, 7: 1, 9: 2}


def test_reorder_does_not_depend_on_the_order_of_the_current_ids():
    assert compute_reorder({9, 1, 5}, [5, 9, 1]) == {5: 0, 9: 1, 1: 2}


def test_reorder_of_nothing_is_nothing():
    assert compute_reorder([], []) == {}


def test_reorder_of_a_single_category():
    assert compute_reorder([4], [4]) == {4: 0}


@pytest.mark.parametrize(
    ("current", "ordered", "fragment"),
    [
        ([1, 2, 3], [1, 2, 2, 3], "repetidas"),  # id repetido
        ([1, 2, 3], [1, 2, 99], "no existen"),  # id inexistente
        ([1, 2, 3], [1, 2], "todas"),  # falta una
        ([1, 2, 3], [], "todas"),  # vacía
        ([1, 2], [1, 2, 3], "no existen"),  # sobra una
        ([], [1], "no existen"),  # no hay categorías
    ],
)
def test_an_invalid_reorder_list_is_rejected(current, ordered, fragment):
    with pytest.raises(DomainValidationError) as exc_info:
        compute_reorder(current, ordered)

    assert error_field(exc_info) == "ids"
    assert fragment in exc_info.value.message


def test_a_rejected_reorder_changes_nothing():
    """Es una función pura: ni la lista de entrada ni las categorías se tocan."""
    current, ordered = [1, 2, 3], [3, 2, 2]

    with pytest.raises(DomainValidationError):
        compute_reorder(current, ordered)

    assert current == [1, 2, 3]
    assert ordered == [3, 2, 2]
