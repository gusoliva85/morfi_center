import json

import pytest
from sqlalchemy import select

from app.core.enums import Role, UserStatus
from app.core.security import create_access_token, hash_password
from app.models import AuditLog, Cart, CustomerBalance, User
from app.repositories.user_repository import UserRepository

USERS = "/api/v1/users"
LOGIN = "/api/v1/auth/login"

PASSWORD = "secreta123"


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def make_user(session):
    def make(role: Role, email: str | None = None, status: UserStatus = UserStatus.ACTIVE) -> User:
        user = UserRepository(session).create(
            first_name="Test",
            last_name=role.value.title(),
            email=email or f"{role.value.lower()}-{id(role)}@example.com",
            password_hash=hash_password(PASSWORD),
            role=role,
            status=status,
        )
        session.flush()
        return user

    return make


@pytest.fixture()
def admin(make_user):
    return make_user(Role.ADMIN, email="admin@example.com")


@pytest.fixture()
def admin_token(admin):
    return create_access_token(admin)


# ---------- listado ----------


async def test_the_listing_returns_the_paginated_shape(client, admin_token):
    response = await client.get(USERS, headers=auth(admin_token))

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"items", "page", "page_size", "total"}
    assert body["page"] == 1
    assert body["page_size"] == 20


async def test_the_listing_shows_every_user(client, admin_token, make_user):
    make_user(Role.CUSTOMER, email="c1@example.com")
    make_user(Role.DELIVERY, email="d1@example.com")

    response = await client.get(USERS, headers=auth(admin_token))

    assert response.json()["total"] == 3  # admin + cliente + repartidor


async def test_the_listing_filters_by_role(client, admin_token, make_user):
    make_user(Role.CUSTOMER, email="c1@example.com")
    make_user(Role.CUSTOMER, email="c2@example.com")
    make_user(Role.DELIVERY, email="d1@example.com")

    response = await client.get(f"{USERS}?role={Role.CUSTOMER.value}", headers=auth(admin_token))

    body = response.json()
    assert body["total"] == 2
    assert {u["role"] for u in body["items"]} == {Role.CUSTOMER.value}


async def test_the_listing_paginates_and_the_total_is_global(client, admin_token, make_user):
    for i in range(4):
        make_user(Role.CUSTOMER, email=f"c{i}@example.com")

    first = await client.get(f"{USERS}?page=1&page_size=2", headers=auth(admin_token))
    second = await client.get(f"{USERS}?page=2&page_size=2", headers=auth(admin_token))

    assert len(first.json()["items"]) == 2
    assert len(second.json()["items"]) == 2
    assert first.json()["total"] == second.json()["total"] == 5  # 4 clientes + admin
    assert first.json()["items"] != second.json()["items"]


async def test_a_page_beyond_the_last_one_is_empty(client, admin_token):
    response = await client.get(f"{USERS}?page=99", headers=auth(admin_token))

    assert response.status_code == 200
    assert response.json()["items"] == []


async def test_the_listing_includes_each_users_status(client, admin_token, make_user):
    """Sin esto, el panel de admin no podría distinguir a quién ofrecerle
    "Suspender" y a quién "Reactivar"."""
    make_user(Role.CUSTOMER, email="activo@example.com", status=UserStatus.ACTIVE)
    make_user(Role.CUSTOMER, email="suspendido@example.com", status=UserStatus.SUSPENDED)

    response = await client.get(USERS, headers=auth(admin_token))

    by_email = {u["email"]: u["status"] for u in response.json()["items"]}
    assert by_email["activo@example.com"] == UserStatus.ACTIVE.value
    assert by_email["suspendido@example.com"] == UserStatus.SUSPENDED.value


async def test_the_listing_never_exposes_password_hashes(client, admin_token, make_user):
    make_user(Role.CUSTOMER, email="c1@example.com")

    response = await client.get(USERS, headers=auth(admin_token))

    assert "password" not in response.text


@pytest.mark.parametrize("query", ["page=0", "page_size=0", "page_size=500", "role=SUPERMAN"])
async def test_invalid_query_params_are_rejected(client, admin_token, query):
    """El tope de `page_size` importa: sin él, `?page_size=999999` traería la
    tabla completa en una sola respuesta."""
    response = await client.get(f"{USERS}?{query}", headers=auth(admin_token))

    assert response.status_code == 422


async def test_a_customer_cannot_list_users(client, make_user):
    token = create_access_token(make_user(Role.CUSTOMER, email="c1@example.com"))

    response = await client.get(USERS, headers=auth(token))

    assert response.status_code == 403


async def test_listing_without_a_session_is_401(client):
    response = await client.get(USERS)

    assert response.status_code == 401


# ---------- edición ----------


async def test_an_admin_can_suspend_a_user(client, session, admin_token, make_user):
    target = make_user(Role.CUSTOMER, email="c1@example.com")

    response = await client.patch(
        f"{USERS}/{target.id}",
        json={"status": UserStatus.SUSPENDED.value},
        headers=auth(admin_token),
    )

    assert response.status_code == 200
    session.expire_all()
    assert session.get(User, target.id).status == UserStatus.SUSPENDED


async def test_a_suspended_user_cannot_log_in(client, session, admin_token, make_user):
    target = make_user(Role.CUSTOMER, email="c1@example.com")
    await client.patch(
        f"{USERS}/{target.id}",
        json={"status": UserStatus.SUSPENDED.value},
        headers=auth(admin_token),
    )

    response = await client.post(LOGIN, json={"email": "c1@example.com", "password": PASSWORD})

    assert response.status_code == 403


async def test_a_reactivated_user_can_log_in_again(client, session, admin_token, make_user):
    target = make_user(Role.CUSTOMER, email="c1@example.com", status=UserStatus.SUSPENDED)

    await client.patch(
        f"{USERS}/{target.id}",
        json={"status": UserStatus.ACTIVE.value},
        headers=auth(admin_token),
    )

    response = await client.post(LOGIN, json={"email": "c1@example.com", "password": PASSWORD})
    assert response.status_code == 200


async def test_an_admin_can_change_a_role(client, session, admin_token, make_user):
    target = make_user(Role.CUSTOMER, email="c1@example.com")

    response = await client.patch(
        f"{USERS}/{target.id}", json={"role": Role.DELIVERY.value}, headers=auth(admin_token)
    )

    assert response.json()["role"] == Role.DELIVERY.value
    session.expire_all()
    assert session.get(User, target.id).role == Role.DELIVERY


async def test_promoting_to_customer_creates_the_cart_and_the_balance(
    client, session, admin_token, make_user
):
    """Un usuario que pasa a CUSTOMER sin carrito ni saldo quedaría como cliente
    a medias, sin poder pedir nada."""
    target = make_user(Role.DELIVERY, email="d1@example.com")
    assert target.cart is None

    await client.patch(
        f"{USERS}/{target.id}", json={"role": Role.CUSTOMER.value}, headers=auth(admin_token)
    )

    session.expire_all()
    updated = session.get(User, target.id)
    assert updated.cart is not None
    assert updated.balance.balance == 0


async def test_role_and_status_can_change_together(client, session, admin_token, make_user):
    target = make_user(Role.CUSTOMER, email="c1@example.com")

    response = await client.patch(
        f"{USERS}/{target.id}",
        json={"role": Role.ADMIN.value, "status": UserStatus.SUSPENDED.value},
        headers=auth(admin_token),
    )

    assert response.status_code == 200
    session.expire_all()
    updated = session.get(User, target.id)
    assert (updated.role, updated.status) == (Role.ADMIN, UserStatus.SUSPENDED)


async def test_an_empty_patch_changes_nothing(client, session, admin_token, make_user):
    target = make_user(Role.CUSTOMER, email="c1@example.com")

    response = await client.patch(f"{USERS}/{target.id}", json={}, headers=auth(admin_token))

    assert response.status_code == 200
    session.expire_all()
    assert session.get(User, target.id).role == Role.CUSTOMER


async def test_an_admin_cannot_change_their_own_role_or_status(client, admin, admin_token):
    """Bajarse de rol o suspenderse a sí mismo deja al admin afuera en el acto,
    sin forma de revertirlo desde la app."""
    response = await client.patch(
        f"{USERS}/{admin.id}",
        json={"status": UserStatus.SUSPENDED.value},
        headers=auth(admin_token),
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


async def test_another_admin_can_still_be_edited(client, session, admin_token, make_user):
    other_admin = make_user(Role.ADMIN, email="otro-admin@example.com")

    response = await client.patch(
        f"{USERS}/{other_admin.id}",
        json={"status": UserStatus.SUSPENDED.value},
        headers=auth(admin_token),
    )

    assert response.status_code == 200


async def test_editing_someone_who_does_not_exist_is_404(client, admin_token):
    response = await client.patch(
        f"{USERS}/99999", json={"status": UserStatus.SUSPENDED.value}, headers=auth(admin_token)
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.parametrize(
    "payload",
    [
        {"role": "SUPERMAN"},
        {"status": "DORMIDO"},
        {"email": "otro@example.com"},
        {"first_name": "Otro"},
        {"password": "otra-clave-9"},
    ],
)
async def test_invalid_or_forbidden_fields_are_rejected(client, admin_token, make_user, payload):
    target = make_user(Role.CUSTOMER, email="c1@example.com")

    response = await client.patch(f"{USERS}/{target.id}", json=payload, headers=auth(admin_token))

    assert response.status_code == 422


async def test_a_customer_cannot_edit_users(client, session, make_user):
    target = make_user(Role.CUSTOMER, email="c1@example.com")
    attacker = make_user(Role.CUSTOMER, email="c2@example.com")

    response = await client.patch(
        f"{USERS}/{target.id}",
        json={"role": Role.ADMIN.value},
        headers=auth(create_access_token(attacker)),
    )

    assert response.status_code == 403
    session.expire_all()
    assert session.get(User, target.id).role == Role.CUSTOMER


# ---------- auditoría ----------


async def test_a_change_is_recorded_in_the_audit_log(
    client, session, admin, admin_token, make_user
):
    target = make_user(Role.CUSTOMER, email="c1@example.com")

    await client.patch(
        f"{USERS}/{target.id}",
        json={"status": UserStatus.SUSPENDED.value},
        headers=auth(admin_token),
    )

    entry = session.scalars(select(AuditLog)).one()
    assert entry.action == "user.update"
    assert entry.entity_type == "user"
    assert entry.entity_id == str(target.id)
    assert entry.actor_id == admin.id
    assert entry.created_at is not None


async def test_the_audit_entry_keeps_the_values_before_and_after(
    client, session, admin_token, make_user
):
    target = make_user(Role.CUSTOMER, email="c1@example.com")

    await client.patch(
        f"{USERS}/{target.id}", json={"role": Role.DELIVERY.value}, headers=auth(admin_token)
    )

    data = json.loads(session.scalars(select(AuditLog)).one().data)
    assert data["before"]["role"] == Role.CUSTOMER.value
    assert data["after"]["role"] == Role.DELIVERY.value


async def test_a_patch_that_changes_nothing_is_not_audited(client, session, admin_token, make_user):
    """Auditar cambios que no cambiaron nada llenaría el log de ruido y
    escondería los cambios de verdad."""
    target = make_user(Role.CUSTOMER, email="c1@example.com")

    await client.patch(
        f"{USERS}/{target.id}", json={"role": Role.CUSTOMER.value}, headers=auth(admin_token)
    )
    await client.patch(f"{USERS}/{target.id}", json={}, headers=auth(admin_token))

    assert session.scalars(select(AuditLog)).all() == []


async def test_each_change_adds_its_own_entry(client, session, admin_token, make_user):
    target = make_user(Role.CUSTOMER, email="c1@example.com")

    await client.patch(
        f"{USERS}/{target.id}",
        json={"status": UserStatus.SUSPENDED.value},
        headers=auth(admin_token),
    )
    await client.patch(
        f"{USERS}/{target.id}", json={"status": UserStatus.ACTIVE.value}, headers=auth(admin_token)
    )

    assert len(session.scalars(select(AuditLog)).all()) == 2


async def test_a_rejected_change_leaves_no_audit_trace(client, session, make_user):
    target = make_user(Role.CUSTOMER, email="c1@example.com")
    attacker = make_user(Role.CUSTOMER, email="c2@example.com")

    await client.patch(
        f"{USERS}/{target.id}",
        json={"role": Role.ADMIN.value},
        headers=auth(create_access_token(attacker)),
    )

    assert session.scalars(select(AuditLog)).all() == []


async def test_the_audit_does_not_break_when_a_customer_is_promoted(
    client, session, admin_token, make_user
):
    target = make_user(Role.DELIVERY, email="d1@example.com")

    await client.patch(
        f"{USERS}/{target.id}", json={"role": Role.CUSTOMER.value}, headers=auth(admin_token)
    )

    assert len(session.scalars(select(AuditLog)).all()) == 1
    assert session.scalars(select(Cart)).all() != []
    assert session.scalars(select(CustomerBalance)).all() != []
