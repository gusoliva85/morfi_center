import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from app.core.errors import DomainValidationError
from app.models import Product, ProductImage
from app.repositories.category_repository import CategoryRepository
from app.repositories.product_repository import ProductRepository
from app.services.catalog_service import search_key


@pytest.fixture()
def categories(session):
    repo = CategoryRepository(session)
    return {
        "principales": repo.create("Principales"),
        "pizza": repo.create("Pizza"),
        "postres": repo.create("Postres", is_active=False),
    }


@pytest.fixture()
def repo(session, categories) -> ProductRepository:
    return ProductRepository(session)


def add(repo, categories, name, category="principales", price=1000000, **kwargs) -> Product:
    return repo.create(name=name, category_id=categories[category].id, base_price=price, **kwargs)


def names(products) -> list[str]:
    return [p.name for p in products]


def count(session) -> int:
    return session.scalar(select(func.count()).select_from(Product))


# ---------- search_key ----------


@pytest.mark.parametrize(
    ("text_in", "expected"),
    [
        ("Sándwich", "sandwich"),
        ("  Sándwich  DE Milanesa ", "sandwich de milanesa"),
        ("ÑOQUIS", "noquis"),
        ("Milanesa\tnapolitana\n", "milanesa napolitana"),
        ("", ""),
        (None, ""),
    ],
)
def test_search_key_ignores_accents_case_and_extra_spaces(text_in, expected):
    assert search_key(text_in) == expected


# ---------- crear y leer ----------


def test_a_created_product_is_read_back(repo, categories):
    created = add(repo, categories, "Milanesa napolitana", description="Con papas.")

    found = repo.get(created.id)

    assert found is not None
    assert (found.name, found.base_price, found.description) == (
        "Milanesa napolitana",
        1000000,
        "Con papas.",
    )
    assert (found.category_id, found.is_active) == (categories["principales"].id, True)
    assert found.created_at and found.updated_at


def test_create_normalizes_the_fields(repo, categories):
    product = add(repo, categories, "  Milanesa   napolitana ", description="  ")

    assert (product.name, product.description) == ("Milanesa napolitana", None)


def test_get_of_a_missing_product_returns_none(repo):
    assert repo.get(999) is None


def test_new_products_go_to_the_end_of_their_own_category(repo, categories):
    a = add(repo, categories, "A", "principales")
    b = add(repo, categories, "B", "principales")
    c = add(repo, categories, "C", "pizza")  # otra categoría: cuenta desde cero

    assert (a.sort_order, b.sort_order, c.sort_order) == (0, 1, 0)


def test_a_product_can_be_created_in_an_inactive_category(repo, categories):
    assert add(repo, categories, "Flan", "postres").id is not None


def test_a_product_can_start_inactive(repo, categories):
    assert add(repo, categories, "Borrador", is_active=False).is_active is False


@pytest.mark.parametrize("price", [0, -100, 10.5, "100", None])
def test_create_rejects_a_bad_price_and_saves_nothing(repo, session, categories, price):
    """El caso del roadmap: precio 0 o negativo → error."""
    with pytest.raises(DomainValidationError):
        add(repo, categories, "X", price=price)

    assert count(session) == 0


def test_create_rejects_an_unknown_category(repo, session):
    with pytest.raises(DomainValidationError) as exc_info:
        repo.create(name="X", category_id=999, base_price=100)

    assert exc_info.value.details["fields"][0]["field"] == "category_id"
    assert count(session) == 0


def test_create_reports_every_problem_at_once(repo):
    with pytest.raises(DomainValidationError) as exc_info:
        repo.create(name="", category_id=999, base_price=0)

    fields = [f["field"] for f in exc_info.value.details["fields"]]
    assert fields == ["name", "category_id", "base_price"]


# ---------- catálogo público ----------


def test_the_public_list_excludes_inactive_products(repo, categories):
    add(repo, categories, "Visible")
    add(repo, categories, "Oculto", is_active=False)

    assert names(repo.list_public()) == ["Visible"]


def test_the_public_list_excludes_products_of_inactive_categories(repo, categories):
    """El caso del roadmap."""
    add(repo, categories, "Milanesa", "principales")
    add(repo, categories, "Flan", "postres")  # producto activo, categoría inactiva

    assert names(repo.list_public()) == ["Milanesa"]


def test_reactivating_the_category_shows_its_products_again(repo, session, categories):
    add(repo, categories, "Flan", "postres")
    CategoryRepository(session).update(categories["postres"], is_active=True)

    assert names(repo.list_public()) == ["Flan"]


def test_a_product_deactivated_on_its_own_stays_hidden_when_its_category_returns(
    repo, session, categories
):
    flan = add(repo, categories, "Flan", "postres", is_active=False)
    CategoryRepository(session).update(categories["postres"], is_active=True)

    assert repo.list_public() == []
    assert flan.is_active is False


def test_the_public_list_follows_the_menu_order(repo, session, categories):
    add(repo, categories, "Pizza muzzarella", "pizza")
    add(repo, categories, "Milanesa", "principales")
    add(repo, categories, "Guiso", "principales")
    # Pizza pasa adelante en el menú: sus productos también.
    CategoryRepository(session).reorder(
        [categories["pizza"].id, categories["principales"].id, categories["postres"].id]
    )

    assert names(repo.list_public()) == ["Pizza muzzarella", "Milanesa", "Guiso"]


def test_products_of_a_category_keep_their_own_position_order(repo, session, categories):
    a = add(repo, categories, "A")
    b = add(repo, categories, "B")
    a.sort_order, b.sort_order = 5, 2
    session.flush()

    assert names(repo.list_public()) == ["B", "A"]


def test_the_public_list_filters_by_category(repo, categories):
    add(repo, categories, "Milanesa", "principales")
    add(repo, categories, "Pizza muzzarella", "pizza")

    assert names(repo.list_public(category_id=categories["pizza"].id)) == ["Pizza muzzarella"]


def test_filtering_by_an_inactive_or_unknown_category_returns_nothing(repo, categories):
    add(repo, categories, "Flan", "postres")

    assert repo.list_public(category_id=categories["postres"].id) == []
    assert repo.list_public(category_id=999) == []


def test_the_public_list_is_empty_without_products(repo):
    assert repo.list_public() == []


# ---------- búsqueda ----------


@pytest.fixture()
def menu(repo, categories):
    add(repo, categories, "Milanesa napolitana", description="Con papas fritas y salsa.")
    add(repo, categories, "Sándwich de milanesa", description="En pan de miga.")
    add(repo, categories, "Guiso de lentejas")
    add(repo, categories, "Ñoquis con salsa", "pizza")


def test_search_ignores_case(repo, menu):
    assert names(repo.list_public(search="MILANESA")) == [
        "Milanesa napolitana",
        "Sándwich de milanesa",
    ]


def test_search_ignores_accents_in_both_directions(repo, menu):
    assert names(repo.list_public(search="sandwich")) == ["Sándwich de milanesa"]
    assert names(repo.list_public(search="ñoquis")) == ["Ñoquis con salsa"]
    assert names(repo.list_public(search="noquis")) == ["Ñoquis con salsa"]


def test_search_also_looks_in_the_description(repo, menu):
    assert names(repo.list_public(search="papas")) == ["Milanesa napolitana"]


def test_every_search_word_has_to_match(repo, menu):
    assert names(repo.list_public(search="milanesa papas")) == ["Milanesa napolitana"]
    assert repo.list_public(search="milanesa lentejas") == []


def test_words_may_match_in_any_order_and_partially(repo, menu):
    assert names(repo.list_public(search="papas mila")) == ["Milanesa napolitana"]


@pytest.mark.parametrize("blank", [None, "", "   "])
def test_a_blank_search_does_not_filter(repo, menu, blank):
    assert len(repo.list_public(search=blank)) == 4


def test_a_search_with_no_match_returns_nothing(repo, menu):
    assert repo.list_public(search="paella") == []


def test_search_and_category_filter_combine(repo, menu, categories):
    result = repo.list_public(category_id=categories["pizza"].id, search="salsa")

    assert names(result) == ["Ñoquis con salsa"]
    assert repo.list_public(category_id=categories["pizza"].id, search="milanesa") == []


def test_search_never_shows_hidden_products(repo, categories):
    add(repo, categories, "Milanesa oculta", is_active=False)
    add(repo, categories, "Milanesa de postre", "postres")

    assert repo.list_public(search="milanesa") == []


# ---------- actualizar ----------


def test_update_changes_only_what_it_is_given(repo, categories):
    product = add(repo, categories, "Milanesa", description="Rica.")

    repo.update(product, base_price=1250000)

    assert (product.name, product.description, product.base_price) == (
        "Milanesa",
        "Rica.",
        1250000,
    )


def test_update_can_move_a_product_to_another_category(repo, categories):
    product = add(repo, categories, "Milanesa")

    repo.update(product, category_id=categories["pizza"].id)

    assert product.category_id == categories["pizza"].id


def test_update_can_clear_the_description(repo, categories):
    product = add(repo, categories, "Milanesa", description="Rica.")

    repo.update(product, description=None)

    assert product.description is None


@pytest.mark.parametrize(
    "changes",
    [{"base_price": 0}, {"name": "  "}, {"category_id": 999}, {"id": 7}, {"name": None}],
)
def test_update_with_invalid_data_changes_nothing(repo, categories, changes):
    product = add(repo, categories, "Milanesa", price=1000000)

    with pytest.raises(DomainValidationError):
        repo.update(product, **changes)

    assert (product.name, product.base_price, product.category_id) == (
        "Milanesa",
        1000000,
        categories["principales"].id,
    )


def test_update_touches_updated_at(repo, categories):
    product = add(repo, categories, "Milanesa")
    before = product.updated_at

    repo.update(product, name="Milanesa completa")

    assert product.updated_at >= before


def test_set_active_hides_and_shows_a_product(repo, categories):
    product = add(repo, categories, "Milanesa")

    repo.set_active(product, False)
    assert repo.list_public() == []

    repo.set_active(product, True)
    assert names(repo.list_public()) == ["Milanesa"]


def test_set_active_rejects_a_non_boolean(repo, categories):
    product = add(repo, categories, "Milanesa")

    with pytest.raises(DomainValidationError):
        repo.set_active(product, "no")

    assert product.is_active is True


# ---------- la base también protege ----------


def raw_insert_product(session, *, price=100, category_id=1):
    session.execute(
        text(
            "INSERT INTO products (category_id, name, base_price, is_active, sort_order, "
            "created_at, updated_at) VALUES "
            "(:c, 'X', :p, 1, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ),
        {"c": category_id, "p": price},
    )


@pytest.mark.parametrize("price", [0, -1])
def test_the_database_itself_rejects_a_non_positive_price(session, categories, price):
    with pytest.raises(IntegrityError):
        raw_insert_product(session, price=price, category_id=categories["principales"].id)


def test_the_database_rejects_a_product_with_a_missing_category(session, categories):
    with pytest.raises(IntegrityError):
        raw_insert_product(session, category_id=999)


def test_a_category_with_products_cannot_be_deleted(session, repo, categories):
    add(repo, categories, "Milanesa")

    with pytest.raises(IntegrityError):
        session.execute(
            text("DELETE FROM categories WHERE id = :id"), {"id": categories["principales"].id}
        )


# ---------- imágenes ----------


def test_images_come_back_in_order_with_the_product(repo, session, categories):
    product = add(repo, categories, "Milanesa")
    session.add_all(
        [
            ProductImage(product_id=product.id, path="products/b.jpg", sort_order=2),
            ProductImage(
                product_id=product.id, path="products/a.jpg", sort_order=1, is_primary=True
            ),
        ]
    )
    session.flush()
    session.expire_all()

    images = repo.get(product.id).images

    assert [(i.path, i.is_primary) for i in images] == [
        ("products/a.jpg", True),
        ("products/b.jpg", False),
    ]


def test_an_image_is_not_primary_by_default(repo, session, categories):
    product = add(repo, categories, "Milanesa")
    image = ProductImage(product_id=product.id, path="products/a.jpg")
    session.add(image)
    session.flush()

    assert (image.is_primary, image.sort_order) == (False, 0)


def test_deleting_a_product_deletes_its_images(repo, session, categories):
    product = add(repo, categories, "Milanesa")
    session.add(ProductImage(product_id=product.id, path="products/a.jpg"))
    session.flush()

    session.delete(product)
    session.flush()

    assert session.scalar(select(func.count()).select_from(ProductImage)) == 0


def test_the_database_cascades_the_deletion_of_images(repo, session, categories):
    """Aunque se borre el producto por fuera del ORM (SQL directo)."""
    product = add(repo, categories, "Milanesa")
    session.add(ProductImage(product_id=product.id, path="products/a.jpg"))
    session.flush()

    session.execute(text("DELETE FROM products WHERE id = :id"), {"id": product.id})

    assert session.scalar(select(func.count()).select_from(ProductImage)) == 0


def test_the_public_list_brings_images_and_category_loaded(repo, session, categories):
    product = add(repo, categories, "Milanesa")
    session.add(ProductImage(product_id=product.id, path="products/a.jpg", is_primary=True))
    session.flush()
    session.expire_all()

    (listed,) = repo.list_public()

    assert [i.path for i in listed.images] == ["products/a.jpg"]
    assert listed.category.name == "Principales"
