import pytest

from app.core.errors import DomainValidationError
from app.services.catalog_service import (
    MAX_PRICE_CENTS,
    PRODUCT_DESCRIPTION_MAX,
    PRODUCT_NAME_MAX,
    ProductData,
    validate_base_price,
    validate_category_reference,
    validate_description,
    validate_is_active,
    validate_new_product,
    validate_product_changes,
    validate_product_name,
)

CATEGORIES = {1, 2, 3}
VALID = {"name": "Milanesa napolitana", "category_id": 1, "base_price": 1150000}


def fields_of(exc_info) -> list[str]:
    return [f["field"] for f in exc_info.value.details["fields"]]


# ---------- nombre ----------


def test_the_name_is_trimmed_and_inner_spaces_collapsed():
    assert validate_product_name("  Milanesa   con\tpapas ") == "Milanesa con papas"


@pytest.mark.parametrize("name", [None, "", "   ", "\n", 123, ["x"]])
def test_a_missing_or_blank_name_is_rejected(name):
    with pytest.raises(DomainValidationError) as exc_info:
        validate_product_name(name)

    assert fields_of(exc_info) == ["name"]


def test_the_name_length_limit_is_inclusive():
    assert validate_product_name("a" * PRODUCT_NAME_MAX) == "a" * PRODUCT_NAME_MAX

    with pytest.raises(DomainValidationError):
        validate_product_name("a" * (PRODUCT_NAME_MAX + 1))


@pytest.mark.parametrize("name", ["???", "- -", "¡!"])
def test_a_name_without_letters_or_numbers_is_rejected(name):
    with pytest.raises(DomainValidationError):
        validate_product_name(name)


# ---------- precio ----------


@pytest.mark.parametrize("price", [1, 100, 1150000, MAX_PRICE_CENTS])
def test_a_positive_integer_price_in_cents_is_accepted(price):
    assert validate_base_price(price) == price


@pytest.mark.parametrize("price", [0, -1, -1150000])
def test_a_zero_or_negative_price_is_rejected(price):
    """El caso del roadmap."""
    with pytest.raises(DomainValidationError) as exc_info:
        validate_base_price(price)

    assert fields_of(exc_info) == ["base_price"]
    assert "mayor que cero" in exc_info.value.message


@pytest.mark.parametrize("price", [10.5, 100.0, "100", "", None, True, False, [100]])
def test_a_price_that_is_not_a_plain_integer_is_rejected(price):
    """Sin flotantes (errores de redondeo), ni texto, ni booleanos (`True` es un 1)."""
    with pytest.raises(DomainValidationError) as exc_info:
        validate_base_price(price)

    assert "entero" in exc_info.value.message


def test_a_price_above_the_sanity_cap_is_rejected():
    """Protege de un cero de más: $10.000 tipeado como $10.000.000."""
    with pytest.raises(DomainValidationError) as exc_info:
        validate_base_price(MAX_PRICE_CENTS + 1)

    assert "1.000.000" in exc_info.value.message


# ---------- descripción ----------


@pytest.mark.parametrize("description", [None, "", "   ", "\n\t "])
def test_a_missing_or_blank_description_means_no_description(description):
    assert validate_description(description) is None


def test_the_description_is_trimmed_but_keeps_inner_line_breaks():
    assert validate_description("  Con papas.\nY ensalada.  ") == "Con papas.\nY ensalada."


def test_the_description_length_limit_is_inclusive():
    assert validate_description("a" * PRODUCT_DESCRIPTION_MAX) == "a" * PRODUCT_DESCRIPTION_MAX

    with pytest.raises(DomainValidationError) as exc_info:
        validate_description("a" * (PRODUCT_DESCRIPTION_MAX + 1))
    assert fields_of(exc_info) == ["description"]


def test_a_description_that_is_not_text_is_rejected():
    with pytest.raises(DomainValidationError):
        validate_description(42)


# ---------- categoría ----------


def test_an_existing_category_is_accepted():
    assert validate_category_reference(2, CATEGORIES) == 2


@pytest.mark.parametrize("category_id", [99, 0, -1, None, "1", 1.0, True])
def test_a_missing_category_is_rejected(category_id):
    """El caso del roadmap (y sus variantes: nulo, texto, flotante, booleano)."""
    with pytest.raises(DomainValidationError) as exc_info:
        validate_category_reference(category_id, CATEGORIES)

    assert fields_of(exc_info) == ["category_id"]
    assert exc_info.value.status_code == 422


def test_there_is_nothing_to_reference_when_there_are_no_categories():
    with pytest.raises(DomainValidationError):
        validate_category_reference(1, set())


# ---------- activación ----------


@pytest.mark.parametrize("value", [True, False])
def test_a_boolean_is_accepted_as_activation(value):
    assert validate_is_active(value) is value


@pytest.mark.parametrize("value", [None, 1, 0, "true", "false", ""])
def test_anything_but_a_boolean_is_rejected_as_activation(value):
    with pytest.raises(DomainValidationError):
        validate_is_active(value)


# ---------- alta ----------


def test_a_valid_product_is_normalized_into_product_data():
    product = validate_new_product(
        {**VALID, "name": "  Milanesa   napolitana ", "description": " Con papas. "}, CATEGORIES
    )

    assert product == ProductData(
        name="Milanesa napolitana",
        category_id=1,
        base_price=1150000,
        description="Con papas.",
        is_active=True,
    )


def test_a_new_product_is_active_and_has_no_description_by_default():
    product = validate_new_product(VALID, CATEGORIES)

    assert (product.is_active, product.description) == (True, None)


def test_a_new_product_can_start_inactive():
    assert validate_new_product({**VALID, "is_active": False}, CATEGORIES).is_active is False


def test_a_product_in_an_inactive_category_is_valid():
    """La categoría solo tiene que existir: que esté oculta no impide cargarle productos."""
    assert validate_new_product({**VALID, "category_id": 3}, CATEGORIES).category_id == 3


def test_a_product_with_a_free_price_is_rejected():
    with pytest.raises(DomainValidationError) as exc_info:
        validate_new_product({**VALID, "base_price": 0}, CATEGORIES)

    assert fields_of(exc_info) == ["base_price"]


def test_a_product_with_an_unknown_category_is_rejected():
    with pytest.raises(DomainValidationError) as exc_info:
        validate_new_product({**VALID, "category_id": 99}, CATEGORIES)

    assert fields_of(exc_info) == ["category_id"]


def test_every_problem_is_reported_at_once():
    """Un formulario los muestra juntos, no de a uno por intento."""
    with pytest.raises(DomainValidationError) as exc_info:
        validate_new_product(
            {"name": "  ", "category_id": 99, "base_price": -5, "is_active": "si"}, CATEGORIES
        )

    assert fields_of(exc_info) == ["name", "category_id", "base_price", "is_active"]


def test_an_empty_product_reports_the_required_fields():
    with pytest.raises(DomainValidationError) as exc_info:
        validate_new_product({}, CATEGORIES)

    assert fields_of(exc_info) == ["name", "category_id", "base_price"]


# ---------- edición (PATCH) ----------


def test_an_edit_validates_and_returns_only_the_fields_it_was_given():
    changes = validate_product_changes({"name": "  Otra  cosa ", "base_price": 900000}, CATEGORIES)

    assert changes == {"name": "Otra cosa", "base_price": 900000}


def test_an_empty_edit_is_valid_and_changes_nothing():
    assert validate_product_changes({}, CATEGORIES) == {}


def test_an_edit_can_clear_the_description_with_none():
    assert validate_product_changes({"description": None}, CATEGORIES) == {"description": None}
    assert validate_product_changes({"description": "  "}, CATEGORIES) == {"description": None}


@pytest.mark.parametrize("field", ["name", "category_id", "base_price", "is_active"])
def test_an_edit_cannot_set_a_required_field_to_none(field):
    with pytest.raises(DomainValidationError) as exc_info:
        validate_product_changes({field: None}, CATEGORIES)

    assert fields_of(exc_info) == [field]


def test_an_edit_applies_the_same_price_rule():
    with pytest.raises(DomainValidationError) as exc_info:
        validate_product_changes({"base_price": 0}, CATEGORIES)

    assert fields_of(exc_info) == ["base_price"]


def test_an_edit_validates_the_category_only_when_it_is_sent():
    assert validate_product_changes({"name": "X"}, set()) == {"name": "X"}  # sin categorías, igual

    with pytest.raises(DomainValidationError):
        validate_product_changes({"category_id": 99}, CATEGORIES)


def test_an_edit_can_deactivate_and_move_a_product():
    changes = validate_product_changes({"is_active": False, "category_id": 2}, CATEGORIES)

    assert changes == {"is_active": False, "category_id": 2}


def test_an_edit_of_a_field_that_cannot_be_edited_is_rejected():
    with pytest.raises(DomainValidationError) as exc_info:
        validate_product_changes({"id": 5}, CATEGORIES)

    assert fields_of(exc_info) == ["id"]


def test_an_edit_reports_every_invalid_field_together():
    with pytest.raises(DomainValidationError) as exc_info:
        validate_product_changes({"name": "", "base_price": -1}, CATEGORIES)

    assert fields_of(exc_info) == ["name", "base_price"]
