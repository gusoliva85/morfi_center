import json

import pytest
from sqlalchemy import func, select

from app.core.enums import Role
from app.core.security import create_access_token, hash_password
from app.models import AuditLog, Product, User
from app.repositories.category_repository import CategoryRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.user_repository import UserRepository

PRODUCTS = "/api/v1/catalog/products"


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
def admin(make_user):
    return make_user(Role.ADMIN, "admin@example.com")


@pytest.fixture()
def h(admin):
    return auth(create_access_token(admin))


@pytest.fixture()
def cats(session):
    repo = CategoryRepository(session)
    return {
        "principales": repo.create("Principales"),
        "pizza": repo.create("Pizza"),
        "postres": repo.create("Postres", is_active=False),
    }


def body(cats, **overrides):
    return {
        "name": "Milanesa napolitana",
        "category_id": cats["principales"].id,
        "base_price": 1150000,
        **overrides,
    }


@pytest.fixture()
def product(session, cats) -> Product:
    return ProductRepository(session).create(
        name="Milanesa",
        category_id=cats["principales"].id,
        base_price=1000000,
        description="Rica.",
    )


def count(session) -> int:
    return session.scalar(select(func.count()).select_from(Product))


def audits(session, action: str | None = None) -> list[AuditLog]:
    query = select(AuditLog).where(AuditLog.entity_type == "product").order_by(AuditLog.id)
    return [a for a in session.scalars(query) if action is None or a.action == action]


def public_names(session) -> list[str]:
    return [p.name for p in ProductRepository(session).list_public()]


# ---------- alta ----------


async def test_the_admin_creates_a_product(client, session, cats, h):
    response = await client.post(PRODUCTS, json=body(cats, description="Con papas."), headers=h)

    assert response.status_code == 201
    created = response.json()
    assert created | {"id": 0} == {
        "id": 0,
        "category_id": cats["principales"].id,
        "name": "Milanesa napolitana",
        "description": "Con papas.",
        "base_price": 1150000,
        "is_active": True,
        "sort_order": 0,
        "images": [],
    }
    assert count(session) == 1
    assert session.get(Product, created["id"]).name == "Milanesa napolitana"


async def test_a_new_product_is_visible_in_the_public_catalog(client, session, cats, h):
    await client.post(PRODUCTS, json=body(cats), headers=h)

    assert public_names(session) == ["Milanesa napolitana"]


async def test_a_product_can_be_created_inactive_and_stays_hidden(client, session, cats, h):
    response = await client.post(PRODUCTS, json=body(cats, is_active=False), headers=h)

    assert response.json()["is_active"] is False
    assert public_names(session) == []


async def test_a_product_can_be_created_in_an_inactive_category(client, cats, h):
    response = await client.post(
        PRODUCTS, json=body(cats, category_id=cats["postres"].id), headers=h
    )

    assert response.status_code == 201


async def test_the_fields_are_normalized_on_creation(client, cats, h):
    response = await client.post(
        PRODUCTS, json=body(cats, name="  Milanesa   napolitana ", description="   "), headers=h
    )

    assert response.json()["name"] == "Milanesa napolitana"
    assert response.json()["description"] is None


@pytest.mark.parametrize("price", [0, -100, 10.5, "100", None, True])
async def test_a_bad_price_answers_422_and_creates_nothing(client, session, cats, h, price):
    """El caso del roadmap: precio 0 o negativo → error."""
    response = await client.post(PRODUCTS, json=body(cats, base_price=price), headers=h)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["details"]["fields"][0]["field"] == "base_price"
    assert count(session) == 0
    assert audits(session) == []


async def test_an_unknown_category_answers_422(client, session, cats, h):
    response = await client.post(PRODUCTS, json=body(cats, category_id=999), headers=h)

    assert response.status_code == 422
    assert response.json()["error"]["details"]["fields"][0]["field"] == "category_id"
    assert count(session) == 0


async def test_every_invalid_field_is_reported_together(client, cats, h):
    response = await client.post(
        PRODUCTS, json={"name": "  ", "category_id": 999, "base_price": 0}, headers=h
    )

    fields = [f["field"] for f in response.json()["error"]["details"]["fields"]]
    assert fields == ["name", "category_id", "base_price"]


async def test_an_empty_body_reports_the_required_fields(client, h):
    response = await client.post(PRODUCTS, json={}, headers=h)

    fields = [f["field"] for f in response.json()["error"]["details"]["fields"]]
    assert fields == ["name", "category_id", "base_price"]


@pytest.mark.parametrize("extra", [{"id": 5}, {"sort_order": 3}, {"images": []}])
async def test_fields_that_cannot_be_set_are_rejected(client, cats, h, extra):
    response = await client.post(PRODUCTS, json={**body(cats), **extra}, headers=h)

    assert response.status_code == 422


@pytest.mark.parametrize("role", [Role.CUSTOMER, Role.DELIVERY])
async def test_other_roles_cannot_create(client, session, cats, make_user, role):
    token = create_access_token(make_user(role, "otro@example.com"))

    response = await client.post(PRODUCTS, json=body(cats), headers=auth(token))

    assert response.status_code == 403
    assert count(session) == 0


async def test_creating_without_a_session_answers_401(client, cats):
    assert (await client.post(PRODUCTS, json=body(cats))).status_code == 401


# ---------- edición ----------


async def test_the_admin_edits_a_product(client, session, product, h):
    response = await client.patch(
        f"{PRODUCTS}/{product.id}",
        json={"base_price": 1250000, "name": "Milanesa completa"},
        headers=h,
    )

    assert response.status_code == 200
    assert (response.json()["name"], response.json()["base_price"]) == (
        "Milanesa completa",
        1250000,
    )
    session.expire_all()
    assert session.get(Product, product.id).base_price == 1250000


async def test_a_patch_only_changes_what_it_sends(client, product, h):
    body_ = (
        await client.patch(f"{PRODUCTS}/{product.id}", json={"base_price": 5}, headers=h)
    ).json()

    assert (body_["name"], body_["description"]) == ("Milanesa", "Rica.")


async def test_a_product_can_be_moved_to_another_category(client, cats, product, h):
    response = await client.patch(
        f"{PRODUCTS}/{product.id}", json={"category_id": cats["pizza"].id}, headers=h
    )

    assert response.json()["category_id"] == cats["pizza"].id


async def test_the_description_is_cleared_with_null(client, product, h):
    response = await client.patch(f"{PRODUCTS}/{product.id}", json={"description": None}, headers=h)

    assert response.json()["description"] is None


@pytest.mark.parametrize(
    "changes",
    [
        {"base_price": 0},
        {"name": "  "},
        {"name": None},
        {"category_id": 999},
        {"is_active": "si"},
        {"name": "", "base_price": -1},
    ],
)
async def test_an_invalid_edit_answers_422_and_changes_nothing(
    client, session, product, h, changes
):
    response = await client.patch(f"{PRODUCTS}/{product.id}", json=changes, headers=h)

    assert response.status_code == 422
    session.expire_all()
    saved = session.get(Product, product.id)
    assert (saved.name, saved.base_price, saved.is_active) == ("Milanesa", 1000000, True)
    assert audits(session) == []


async def test_an_edit_reports_every_invalid_field_together(client, product, h):
    response = await client.patch(
        f"{PRODUCTS}/{product.id}", json={"name": "", "base_price": -1}, headers=h
    )

    fields = [f["field"] for f in response.json()["error"]["details"]["fields"]]
    assert fields == ["name", "base_price"]


async def test_unknown_fields_are_rejected_in_an_edit(client, product, h):
    assert (
        await client.patch(f"{PRODUCTS}/{product.id}", json={"id": 9}, headers=h)
    ).status_code == 422


async def test_editing_an_unknown_product_answers_404(client, h):
    response = await client.patch(f"{PRODUCTS}/999", json={"name": "X"}, headers=h)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.parametrize("role", [Role.CUSTOMER, Role.DELIVERY])
async def test_other_roles_cannot_edit(client, session, product, make_user, role):
    token = create_access_token(make_user(role, "otro@example.com"))

    response = await client.patch(
        f"{PRODUCTS}/{product.id}", json={"base_price": 1}, headers=auth(token)
    )

    assert response.status_code == 403
    assert session.get(Product, product.id).base_price == 1000000


# ---------- baja lógica ----------


async def test_delete_is_a_logical_deactivation(client, session, product, h):
    """El caso del roadmap: alta / edición / baja."""
    response = await client.delete(f"{PRODUCTS}/{product.id}", headers=h)

    assert response.status_code == 204
    assert response.content == b""
    session.expire_all()
    saved = session.get(Product, product.id)
    assert saved is not None  # no se borró de la base
    assert saved.is_active is False
    assert public_names(session) == []


async def test_delete_is_idempotent(client, product, h):
    first = await client.delete(f"{PRODUCTS}/{product.id}", headers=h)
    second = await client.delete(f"{PRODUCTS}/{product.id}", headers=h)

    assert (first.status_code, second.status_code) == (204, 204)


async def test_a_deactivated_product_can_be_shown_again_with_a_patch(client, session, product, h):
    await client.delete(f"{PRODUCTS}/{product.id}", headers=h)

    response = await client.patch(f"{PRODUCTS}/{product.id}", json={"is_active": True}, headers=h)

    assert response.json()["is_active"] is True
    assert public_names(session) == ["Milanesa"]


async def test_deleting_an_unknown_product_answers_404(client, h):
    assert (await client.delete(f"{PRODUCTS}/999", headers=h)).status_code == 404


@pytest.mark.parametrize("role", [Role.CUSTOMER, Role.DELIVERY])
async def test_other_roles_cannot_delete(client, session, product, make_user, role):
    token = create_access_token(make_user(role, "otro@example.com"))

    response = await client.delete(f"{PRODUCTS}/{product.id}", headers=auth(token))

    assert response.status_code == 403
    assert session.get(Product, product.id).is_active is True


async def test_deleting_without_a_session_answers_401(client, product):
    assert (await client.delete(f"{PRODUCTS}/{product.id}")).status_code == 401


# ---------- auditoría ----------


async def test_creating_leaves_an_audit_trail(client, session, cats, admin, h):
    created = (await client.post(PRODUCTS, json=body(cats), headers=h)).json()

    (entry,) = audits(session)
    assert entry.action == "product.create"
    assert entry.entity_id == str(created["id"])
    assert entry.actor_id == admin.id
    assert entry.ip
    data = json.loads(entry.data)
    assert "before" not in data
    assert data["after"]["base_price"] == 1150000
    assert data["after"]["name"] == "Milanesa napolitana"


async def test_a_price_change_records_who_changed_it_and_from_what_to_what(
    client, session, product, admin, h
):
    await client.patch(f"{PRODUCTS}/{product.id}", json={"base_price": 1250000}, headers=h)

    (entry,) = audits(session, "product.update")
    assert entry.actor_id == admin.id
    assert entry.entity_id == str(product.id)
    assert json.loads(entry.data) == {
        "before": {"base_price": 1000000},
        "after": {"base_price": 1250000},
    }


async def test_the_audit_only_has_the_fields_that_really_changed(client, session, product, h):
    """Se manda el mismo nombre que ya tenía: no cuenta como cambio."""
    await client.patch(
        f"{PRODUCTS}/{product.id}", json={"name": "Milanesa", "is_active": False}, headers=h
    )

    (entry,) = audits(session, "product.update")
    assert json.loads(entry.data) == {"before": {"is_active": True}, "after": {"is_active": False}}


@pytest.mark.parametrize("changes", [{}, {"base_price": 1000000}, {"name": "  Milanesa  "}])
async def test_an_edit_that_changes_nothing_leaves_no_audit_trail(
    client, session, product, h, changes
):
    response = await client.patch(f"{PRODUCTS}/{product.id}", json=changes, headers=h)

    assert response.status_code == 200
    assert audits(session) == []


async def test_deactivating_leaves_an_audit_trail(client, session, product, admin, h):
    await client.delete(f"{PRODUCTS}/{product.id}", headers=h)

    (entry,) = audits(session)
    assert entry.action == "product.deactivate"
    assert entry.actor_id == admin.id
    assert json.loads(entry.data) == {"before": {"is_active": True}, "after": {"is_active": False}}


async def test_deactivating_twice_audits_only_once(client, session, product, h):
    await client.delete(f"{PRODUCTS}/{product.id}", headers=h)
    await client.delete(f"{PRODUCTS}/{product.id}", headers=h)

    assert len(audits(session, "product.deactivate")) == 1


async def test_a_forbidden_or_failed_request_leaves_no_audit_trail(
    client, session, cats, make_user, product
):
    token = create_access_token(make_user(Role.CUSTOMER, "otro@example.com"))
    await client.post(PRODUCTS, json=body(cats), headers=auth(token))
    await client.patch(f"{PRODUCTS}/{product.id}", json={"base_price": 1}, headers=auth(token))
    await client.delete(f"{PRODUCTS}/{product.id}", headers=auth(token))

    assert audits(session) == []
