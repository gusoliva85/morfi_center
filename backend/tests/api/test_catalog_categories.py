import pytest
from sqlalchemy import func, select

from app.core.enums import Role
from app.core.security import create_access_token, hash_password
from app.models import Category, User
from app.repositories.category_repository import CategoryRepository
from app.repositories.user_repository import UserRepository

CATEGORIES = "/api/v1/catalog/categories"
REORDER = f"{CATEGORIES}/reorder"


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def make_user(session):
    def make(role: Role, email: str) -> User:
        user = UserRepository(session).create(
            first_name="Test",
            last_name=role.value.title(),
            email=email,
            password_hash=hash_password("secreta123"),
            role=role,
        )
        session.flush()
        return user

    return make


@pytest.fixture()
def h(make_user):
    """Headers de un admin."""
    return auth(create_access_token(make_user(Role.ADMIN, "admin@example.com")))


@pytest.fixture()
def seeded(session):
    """Pizza (activa), Postres (inactiva), Pastas (activa), en ese orden."""
    repo = CategoryRepository(session)
    return {
        "pizza": repo.create("Pizza"),
        "postres": repo.create("Postres", is_active=False),
        "pastas": repo.create("Pastas"),
    }


def names(response) -> list[str]:
    return [c["name"] for c in response.json()]


def count(session) -> int:
    return session.scalar(select(func.count()).select_from(Category))


# ---------- GET público ----------


async def test_the_public_listing_shows_only_active_categories_in_menu_order(client, seeded):
    """El caso del roadmap: el público no ve las inactivas."""
    response = await client.get(CATEGORIES)

    assert response.status_code == 200
    assert names(response) == ["Pizza", "Pastas"]


async def test_the_listing_has_the_documented_shape(client, seeded):
    body = (await client.get(CATEGORIES)).json()

    assert body[0] == {
        "id": seeded["pizza"].id,
        "name": "Pizza",
        "slug": "pizza",
        "sort_order": 0,
        "is_active": True,
    }


async def test_the_public_listing_needs_no_session(client, seeded):
    assert (await client.get(CATEGORIES)).status_code == 200


async def test_the_public_listing_ignores_a_bad_token(client, seeded):
    """Sin `all=true` no se mira el token: uno vencido no rompe el menú público."""
    response = await client.get(CATEGORIES, headers=auth("token-invalido"))

    assert response.status_code == 200


async def test_an_empty_catalog_is_an_empty_list(client):
    response = await client.get(CATEGORIES)

    assert (response.status_code, response.json()) == (200, [])


async def test_all_false_is_the_public_listing(client, seeded):
    assert names(await client.get(f"{CATEGORIES}?all=false")) == ["Pizza", "Pastas"]


# ---------- GET ?all=true ----------


async def test_an_admin_sees_every_category_with_all_true(client, seeded, h):
    response = await client.get(f"{CATEGORIES}?all=true", headers=h)

    assert response.status_code == 200
    assert names(response) == ["Pizza", "Postres", "Pastas"]
    assert [c["is_active"] for c in response.json()] == [True, False, True]


async def test_all_true_without_a_session_answers_401(client, seeded):
    assert (await client.get(f"{CATEGORIES}?all=true")).status_code == 401


@pytest.mark.parametrize("role", [Role.CUSTOMER, Role.DELIVERY])
async def test_all_true_is_forbidden_for_other_roles(client, seeded, make_user, role):
    token = create_access_token(make_user(role, "otro@example.com"))

    response = await client.get(f"{CATEGORIES}?all=true", headers=auth(token))

    assert response.status_code == 403


# ---------- POST ----------


async def test_the_admin_creates_a_category(client, session, h):
    response = await client.post(CATEGORIES, json={"name": "Empanadas"}, headers=h)

    assert response.status_code == 201
    assert response.json() | {"id": 0} == {
        "id": 0,
        "name": "Empanadas",
        "slug": "empanadas",
        "sort_order": 0,
        "is_active": True,
    }
    assert count(session) == 1


async def test_a_new_category_appears_in_the_public_menu_at_the_end(client, seeded, h):
    await client.post(CATEGORIES, json={"name": "Empanadas"}, headers=h)

    assert names(await client.get(CATEGORIES)) == ["Pizza", "Pastas", "Empanadas"]


async def test_a_category_can_be_created_inactive_and_stays_hidden(client, h):
    await client.post(CATEGORIES, json={"name": "Postres", "is_active": False}, headers=h)

    assert (await client.get(CATEGORIES)).json() == []


async def test_creating_with_the_same_name_twice_gives_distinct_slugs(client, h):
    first = await client.post(CATEGORIES, json={"name": "Pizza"}, headers=h)
    second = await client.post(CATEGORIES, json={"name": "Pizza"}, headers=h)

    assert (first.json()["slug"], second.json()["slug"]) == ("pizza", "pizza-2")


async def test_the_name_is_normalized(client, h):
    response = await client.post(CATEGORIES, json={"name": "  Plato   del día "}, headers=h)

    assert response.json()["name"] == "Plato del día"


@pytest.mark.parametrize(
    "body", [{"name": ""}, {"name": "   "}, {"name": "???"}, {"name": "x" * 61}]
)
async def test_an_invalid_name_answers_422_and_creates_nothing(client, session, h, body):
    response = await client.post(CATEGORIES, json=body, headers=h)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["details"]["fields"][0]["field"] == "name"
    assert count(session) == 0


@pytest.mark.parametrize("body", [{}, {"name": None}, {"name": "A", "slug": "manual"}])
async def test_a_malformed_body_is_rejected(client, h, body):
    """Incluido mandar un `slug`: se calcula solo, no se elige."""
    assert (await client.post(CATEGORIES, json=body, headers=h)).status_code == 422


@pytest.mark.parametrize("role", [Role.CUSTOMER, Role.DELIVERY])
async def test_other_roles_cannot_create(client, session, make_user, role):
    token = create_access_token(make_user(role, "otro@example.com"))

    response = await client.post(CATEGORIES, json={"name": "Pizza"}, headers=auth(token))

    assert response.status_code == 403
    assert count(session) == 0


async def test_creating_without_a_session_answers_401(client):
    assert (await client.post(CATEGORIES, json={"name": "Pizza"})).status_code == 401


# ---------- PATCH ----------


async def test_renaming_keeps_the_slug(client, seeded, h):
    response = await client.patch(
        f"{CATEGORIES}/{seeded['pizza'].id}", json={"name": "Pizzas al horno"}, headers=h
    )

    assert response.status_code == 200
    assert (response.json()["name"], response.json()["slug"]) == ("Pizzas al horno", "pizza")


async def test_deactivating_hides_a_category_from_the_public(client, seeded, h):
    await client.patch(f"{CATEGORIES}/{seeded['pizza'].id}", json={"is_active": False}, headers=h)

    assert names(await client.get(CATEGORIES)) == ["Pastas"]
    assert "Pizza" in names(await client.get(f"{CATEGORIES}?all=true", headers=h))


async def test_reactivating_shows_it_again_in_its_place(client, seeded, h):
    await client.patch(f"{CATEGORIES}/{seeded['postres'].id}", json={"is_active": True}, headers=h)

    assert names(await client.get(CATEGORIES)) == ["Pizza", "Postres", "Pastas"]


async def test_a_patch_only_changes_what_it_sends(client, seeded, h):
    body = (
        await client.patch(
            f"{CATEGORIES}/{seeded['pizza'].id}", json={"is_active": False}, headers=h
        )
    ).json()

    assert (body["name"], body["sort_order"]) == ("Pizza", 0)


async def test_an_empty_patch_changes_nothing(client, seeded, h):
    response = await client.patch(f"{CATEGORIES}/{seeded['pizza'].id}", json={}, headers=h)

    assert response.status_code == 200
    assert response.json()["name"] == "Pizza"


@pytest.mark.parametrize("body", [{"name": None}, {"is_active": None}, {"slug": "otro"}])
async def test_null_or_unknown_fields_are_rejected_in_a_patch(client, seeded, h, body):
    response = await client.patch(f"{CATEGORIES}/{seeded['pizza'].id}", json=body, headers=h)

    assert response.status_code == 422


async def test_a_blank_name_in_a_patch_is_rejected_and_keeps_the_old_one(
    client, session, seeded, h
):
    response = await client.patch(
        f"{CATEGORIES}/{seeded['pizza'].id}", json={"name": "  "}, headers=h
    )

    assert response.status_code == 422
    assert session.get(Category, seeded["pizza"].id).name == "Pizza"


async def test_patching_an_unknown_category_answers_404(client, h):
    response = await client.patch(f"{CATEGORIES}/999", json={"name": "X"}, headers=h)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.parametrize("role", [Role.CUSTOMER, Role.DELIVERY])
async def test_other_roles_cannot_patch(client, session, seeded, make_user, role):
    token = create_access_token(make_user(role, "otro@example.com"))

    response = await client.patch(
        f"{CATEGORIES}/{seeded['pizza'].id}", json={"name": "Hackeada"}, headers=auth(token)
    )

    assert response.status_code == 403
    assert session.get(Category, seeded["pizza"].id).name == "Pizza"


# ---------- POST /reorder ----------


async def test_the_admin_reorders_and_the_public_menu_follows(client, seeded, h):
    """El caso del roadmap."""
    ids = [seeded["pastas"].id, seeded["postres"].id, seeded["pizza"].id]

    response = await client.post(REORDER, json={"ids": ids}, headers=h)

    assert response.status_code == 200
    assert names(response) == ["Pastas", "Postres", "Pizza"]  # todas, ya ordenadas
    assert [c["sort_order"] for c in response.json()] == [0, 1, 2]
    assert names(await client.get(CATEGORIES)) == ["Pastas", "Pizza"]


@pytest.mark.parametrize(
    "build",
    [
        lambda ids: ids[:-1],  # falta una
        lambda ids: [*ids, 999],  # sobra una que no existe
        lambda ids: [ids[0], *ids],  # repetida
        lambda ids: [],  # vacía
    ],
)
async def test_an_invalid_reorder_answers_422_and_changes_nothing(client, seeded, h, build):
    ids = [seeded["pizza"].id, seeded["postres"].id, seeded["pastas"].id]

    response = await client.post(REORDER, json={"ids": build(ids)}, headers=h)

    assert response.status_code == 422
    assert response.json()["error"]["details"]["fields"][0]["field"] == "ids"
    assert names(await client.get(f"{CATEGORIES}?all=true", headers=h)) == [
        "Pizza",
        "Postres",
        "Pastas",
    ]


@pytest.mark.parametrize("body", [{}, {"ids": "1,2,3"}, {"ids": ["a"]}, {"ids": [1], "x": 1}])
async def test_a_malformed_reorder_body_is_rejected(client, seeded, h, body):
    assert (await client.post(REORDER, json=body, headers=h)).status_code == 422


@pytest.mark.parametrize("role", [Role.CUSTOMER, Role.DELIVERY])
async def test_other_roles_cannot_reorder(client, seeded, make_user, role):
    token = create_access_token(make_user(role, "otro@example.com"))
    ids = [seeded["pastas"].id, seeded["postres"].id, seeded["pizza"].id]

    response = await client.post(REORDER, json={"ids": ids}, headers=auth(token))

    assert response.status_code == 403
    assert names(await client.get(CATEGORIES)) == ["Pizza", "Pastas"]  # sin cambios


async def test_reorder_is_not_mistaken_for_a_category_id(client, h):
    """`/categories/reorder` no cae en `/categories/{id}`."""
    response = await client.post(REORDER, json={"ids": []}, headers=h)

    assert response.status_code == 200
    assert response.json() == []
