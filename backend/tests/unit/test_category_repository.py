import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from app.core.errors import ConflictError, DomainValidationError
from app.models import Category
from app.repositories.category_repository import CategoryRepository


@pytest.fixture()
def repo(session) -> CategoryRepository:
    return CategoryRepository(session)


def names(categories) -> list[str]:
    return [c.name for c in categories]


def count(session) -> int:
    return session.scalar(select(func.count()).select_from(Category))


# ---------- crear ----------


def test_a_created_category_is_read_back(repo):
    created = repo.create("Pizza")

    found = repo.get(created.id)

    assert found is not None
    assert (found.name, found.slug, found.is_active) == ("Pizza", "pizza", True)
    assert found.created_at and found.updated_at


def test_create_normalizes_the_name(repo):
    assert repo.create("  Plato   del  día ").name == "Plato del día"


def test_create_derives_the_slug_from_the_name(repo):
    assert repo.create("Sándwiches").slug == "sandwiches"


def test_names_that_collide_get_distinct_slugs(repo):
    """El caso del roadmap: los tres dan el mismo slug base."""
    slugs = [repo.create(name).slug for name in ("Sándwiches", "Sandwiches", "SÁNDWICHES")]

    assert slugs == ["sandwiches", "sandwiches-2", "sandwiches-3"]


def test_new_categories_go_to_the_end_of_the_menu(repo):
    positions = [repo.create(name).sort_order for name in ("Pizza", "Pastas", "Empanadas")]

    assert positions == [0, 1, 2]


def test_a_new_category_goes_after_the_highest_position_even_with_gaps(repo, session):
    first = repo.create("Pizza")
    first.sort_order = 7
    session.flush()

    assert repo.create("Pastas").sort_order == 8


def test_create_can_start_a_category_inactive(repo):
    assert repo.create("Postres", is_active=False).is_active is False


@pytest.mark.parametrize("name", ["", "   ", "???"])
def test_create_rejects_an_invalid_name_and_saves_nothing(repo, session, name):
    with pytest.raises(DomainValidationError):
        repo.create(name)

    assert count(session) == 0


def test_the_database_itself_rejects_a_duplicate_slug(session):
    """Lo garantiza la base (UNIQUE), no solo el código."""
    session.add(Category(name="A", slug="pizza", sort_order=0, is_active=True))
    session.flush()
    session.add(Category(name="B", slug="pizza", sort_order=1, is_active=True))

    with pytest.raises(IntegrityError):
        session.flush()


def test_a_simultaneous_creation_with_the_same_slug_becomes_a_conflict(repo, session, monkeypatch):
    """Otro request creó "pizza" (y ya guardó) entre nuestra lectura de slugs y
    nuestro insert: la base frena el segundo y sale un 409, no un 500."""
    repo.create("Pizza")
    session.commit()
    monkeypatch.setattr(repo, "_taken_slugs", lambda: set())  # lectura vieja: no ve "pizza"

    with pytest.raises(ConflictError) as exc_info:
        repo.create("Pizza")

    assert exc_info.value.status_code == 409
    assert count(session) == 1


def test_the_session_stays_usable_after_a_slug_conflict(repo, session, monkeypatch):
    repo.create("Pizza")
    session.commit()
    monkeypatch.setattr(repo, "_taken_slugs", lambda: set())
    with pytest.raises(ConflictError):
        repo.create("Pizza")
    monkeypatch.undo()

    assert repo.create("Pastas").slug == "pastas"  # sigue andando


# ---------- listar ----------


def test_the_listings_follow_the_menu_order(repo):
    for name in ("Pizza", "Pastas", "Empanadas"):
        repo.create(name)

    assert names(repo.list_all()) == ["Pizza", "Pastas", "Empanadas"]


def test_equal_positions_are_broken_by_id(repo, session):
    a, b = repo.create("A"), repo.create("B")
    a.sort_order = b.sort_order = 3
    session.flush()

    assert names(repo.list_all()) == ["A", "B"]


def test_list_active_excludes_inactive_categories(repo):
    repo.create("Pizza")
    repo.create("Postres", is_active=False)
    repo.create("Pastas")

    assert names(repo.list_active()) == ["Pizza", "Pastas"]
    assert names(repo.list_all()) == ["Pizza", "Postres", "Pastas"]


def test_the_listings_are_empty_without_categories(repo):
    assert repo.list_all() == []
    assert repo.list_active() == []


def test_get_of_a_missing_category_returns_none(repo):
    assert repo.get(999) is None
    assert repo.get_by_slug("no-existe") is None


def test_a_category_is_found_by_its_slug(repo):
    created = repo.create("Empanadas")

    assert repo.get_by_slug("empanadas").id == created.id


# ---------- actualizar ----------


def test_update_changes_the_name(repo):
    category = repo.create("Pizza")

    repo.update(category, name="  Pizzas  ")

    assert repo.get(category.id).name == "Pizzas"


def test_renaming_does_not_change_the_slug(repo):
    """Para no romper los links que ya apunten a la categoría."""
    category = repo.create("Pizza")

    repo.update(category, name="Pizzas al horno")

    assert category.slug == "pizza"


def test_update_only_touches_what_it_is_given(repo):
    category = repo.create("Pizza")

    repo.update(category, is_active=False)

    assert (category.name, category.is_active) == ("Pizza", False)


def test_a_category_can_be_reactivated(repo):
    category = repo.create("Pizza", is_active=False)

    repo.update(category, is_active=True)

    assert names(repo.list_active()) == ["Pizza"]


def test_update_rejects_an_invalid_name_and_keeps_the_old_one(repo):
    category = repo.create("Pizza")

    with pytest.raises(DomainValidationError):
        repo.update(category, name="   ")

    assert category.name == "Pizza"


def test_update_touches_updated_at(repo):
    category = repo.create("Pizza")
    before = category.updated_at

    repo.update(category, name="Pizzas")

    assert category.updated_at >= before


# ---------- reordenar ----------


def test_reorder_changes_the_menu_order(repo):
    """El caso del roadmap."""
    pizza, pastas, empanadas = (repo.create(n) for n in ("Pizza", "Pastas", "Empanadas"))

    result = repo.reorder([empanadas.id, pizza.id, pastas.id])

    assert names(result) == ["Empanadas", "Pizza", "Pastas"]
    assert [c.sort_order for c in result] == [0, 1, 2]
    assert names(repo.list_active()) == ["Empanadas", "Pizza", "Pastas"]


def test_reorder_also_orders_inactive_categories(repo):
    a, b = repo.create("A"), repo.create("B", is_active=False)

    repo.reorder([b.id, a.id])

    assert names(repo.list_all()) == ["B", "A"]


@pytest.mark.parametrize(
    "build", [lambda ids: ids[:-1], lambda ids: [*ids, 999], lambda ids: [ids[0], *ids]]
)
def test_an_invalid_reorder_changes_nothing(repo, build):
    ids = [repo.create(name).id for name in ("Pizza", "Pastas", "Empanadas")]

    with pytest.raises(DomainValidationError):
        repo.reorder(build(ids))

    assert names(repo.list_all()) == ["Pizza", "Pastas", "Empanadas"]
    assert [c.sort_order for c in repo.list_all()] == [0, 1, 2]


def test_reorder_persists_in_the_database(repo, session):
    a, b = repo.create("A"), repo.create("B")
    repo.reorder([b.id, a.id])

    raw = session.execute(text("SELECT name FROM categories ORDER BY sort_order")).scalars().all()
    assert raw == ["B", "A"]
