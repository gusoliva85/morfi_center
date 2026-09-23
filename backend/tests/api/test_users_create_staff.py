import pytest
from sqlalchemy import func, select

from app.core.enums import AuthProvider, DriverStatus, Role, UserStatus, VehicleType
from app.core.security import create_access_token, hash_password, verify_password
from app.models import Cart, CustomerBalance, User
from app.repositories.user_repository import UserRepository

USERS = "/api/v1/users"
LOGIN = "/api/v1/auth/login"
REGISTER = "/api/v1/auth/register"

PASSWORD = "secreta123"

NEW_DELIVERY = {
    "role": Role.DELIVERY.value,
    "first_name": "Pedro",
    "last_name": "Reparte",
    "email": "pedro@example.com",
    "password": PASSWORD,
    "phone": "1155559999",
    "vehicle_type": VehicleType.MOTO.value,
    "capacity": 4,
}
NEW_ADMIN = {
    "role": Role.ADMIN.value,
    "first_name": "Sofía",
    "last_name": "Jefa",
    "email": "sofia@example.com",
    "password": PASSWORD,
}


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def make_user(session, role: Role) -> User:
    user = UserRepository(session).create(
        first_name="Test",
        last_name=role.value.title(),
        email=f"{role.value.lower()}@example.com",
        password_hash=hash_password(PASSWORD),
        role=role,
    )
    session.flush()
    return user


@pytest.fixture()
def admin_token(session) -> str:
    return create_access_token(make_user(session, Role.ADMIN))


async def test_an_admin_can_create_a_delivery(client, session, admin_token):
    response = await client.post(USERS, json=NEW_DELIVERY, headers=auth(admin_token))

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "pedro@example.com"
    assert body["role"] == Role.DELIVERY.value
    assert body["phone"] == "1155559999"


async def test_the_delivery_gets_its_profile(client, session, admin_token):
    response = await client.post(USERS, json=NEW_DELIVERY, headers=auth(admin_token))

    created = session.get(User, response.json()["id"])
    assert created.profile is not None
    assert created.profile.vehicle_type == VehicleType.MOTO.value
    assert created.profile.capacity == 4


async def test_a_new_delivery_starts_unavailable(client, session, admin_token):
    """No debería aparecer disponible para asignarle pedidos antes de empezar."""
    response = await client.post(USERS, json=NEW_DELIVERY, headers=auth(admin_token))

    created = session.get(User, response.json()["id"])
    assert created.profile.driver_status == DriverStatus.NO_DISPONIBLE


async def test_an_admin_can_create_another_admin(client, admin_token):
    response = await client.post(USERS, json=NEW_ADMIN, headers=auth(admin_token))

    assert response.status_code == 201
    assert response.json()["role"] == Role.ADMIN.value


async def test_the_created_user_can_log_in(client, session, admin_token):
    await client.post(USERS, json=NEW_DELIVERY, headers=auth(admin_token))

    response = await client.post(LOGIN, json={"email": "pedro@example.com", "password": PASSWORD})

    assert response.status_code == 200
    assert response.json()["user"]["role"] == Role.DELIVERY.value


async def test_the_password_is_stored_hashed(client, session, admin_token):
    response = await client.post(USERS, json=NEW_DELIVERY, headers=auth(admin_token))

    created = session.get(User, response.json()["id"])
    assert created.password_hash != PASSWORD
    assert verify_password(PASSWORD, created.password_hash)


async def test_the_response_never_includes_the_password(client, admin_token):
    response = await client.post(USERS, json=NEW_DELIVERY, headers=auth(admin_token))

    assert PASSWORD not in response.text
    assert "password" not in response.text


async def test_it_does_not_return_tokens(client, admin_token):
    """Sin auto-login: crear a alguien no abre su sesión."""
    response = await client.post(USERS, json=NEW_DELIVERY, headers=auth(admin_token))

    assert "access_token" not in response.json()
    assert "mc_refresh" not in response.cookies


async def test_staff_do_not_get_a_cart_or_a_balance(client, session, admin_token):
    await client.post(USERS, json=NEW_DELIVERY, headers=auth(admin_token))

    assert session.scalars(select(Cart)).all() == []
    assert session.scalars(select(CustomerBalance)).all() == []


async def test_the_created_user_is_active_with_a_local_provider(client, session, admin_token):
    response = await client.post(USERS, json=NEW_ADMIN, headers=auth(admin_token))

    created = session.get(User, response.json()["id"])
    assert created.status == UserStatus.ACTIVE
    assert [p.provider for p in created.auth_providers] == [AuthProvider.LOCAL]


async def test_a_customer_cannot_create_users(client, session):
    token = create_access_token(make_user(session, Role.CUSTOMER))

    response = await client.post(USERS, json=NEW_DELIVERY, headers=auth(token))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


async def test_a_delivery_cannot_create_users(client, session):
    token = create_access_token(make_user(session, Role.DELIVERY))

    response = await client.post(USERS, json=NEW_DELIVERY, headers=auth(token))

    assert response.status_code == 403


async def test_without_a_session_it_is_401(client):
    response = await client.post(USERS, json=NEW_DELIVERY)

    assert response.status_code == 401


async def test_a_blocked_attempt_does_not_create_anything(client, session):
    token = create_access_token(make_user(session, Role.CUSTOMER))
    before = session.scalar(select(func.count()).select_from(User))

    await client.post(USERS, json=NEW_DELIVERY, headers=auth(token))

    assert session.scalar(select(func.count()).select_from(User)) == before


async def test_customers_cannot_be_created_here(client, admin_token):
    """Los clientes se registran solos; crearlos acá los dejaría sin carrito."""
    response = await client.post(
        USERS,
        json={**NEW_ADMIN, "role": Role.CUSTOMER.value},
        headers=auth(admin_token),
    )

    assert response.status_code == 422


async def test_a_delivery_without_a_vehicle_is_rejected(client, admin_token):
    payload = {k: v for k, v in NEW_DELIVERY.items() if k != "vehicle_type"}

    response = await client.post(USERS, json=payload, headers=auth(admin_token))

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_an_invalid_vehicle_is_rejected(client, admin_token):
    response = await client.post(
        USERS, json={**NEW_DELIVERY, "vehicle_type": "cohete"}, headers=auth(admin_token)
    )

    assert response.status_code == 422


async def test_an_admin_with_delivery_fields_is_rejected(client, admin_token):
    response = await client.post(
        USERS,
        json={**NEW_ADMIN, "vehicle_type": VehicleType.MOTO.value},
        headers=auth(admin_token),
    )

    assert response.status_code == 422


@pytest.mark.parametrize("capacity", [0, -3])
async def test_a_non_positive_capacity_is_rejected(client, admin_token, capacity):
    response = await client.post(
        USERS, json={**NEW_DELIVERY, "capacity": capacity}, headers=auth(admin_token)
    )

    assert response.status_code == 422


async def test_the_capacity_is_optional(client, session, admin_token):
    payload = {k: v for k, v in NEW_DELIVERY.items() if k != "capacity"}

    response = await client.post(USERS, json=payload, headers=auth(admin_token))

    assert response.status_code == 201
    assert session.get(User, response.json()["id"]).profile.capacity is None


async def test_a_weak_password_is_rejected(client, admin_token):
    response = await client.post(
        USERS, json={**NEW_DELIVERY, "password": "corta"}, headers=auth(admin_token)
    )

    assert response.status_code == 422
    assert "password" in [f["field"] for f in response.json()["error"]["details"]["fields"]]


async def test_a_duplicated_email_is_a_conflict(client, session, admin_token):
    await client.post(USERS, json=NEW_DELIVERY, headers=auth(admin_token))

    response = await client.post(USERS, json=NEW_DELIVERY, headers=auth(admin_token))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"


async def test_it_cannot_take_the_email_of_an_existing_customer(client, admin_token):
    await client.post(
        REGISTER,
        json={
            "first_name": "Ana",
            "last_name": "Cliente",
            "email": "ana@example.com",
            "password": PASSWORD,
        },
    )

    response = await client.post(
        USERS, json={**NEW_ADMIN, "email": "ANA@example.com"}, headers=auth(admin_token)
    )

    assert response.status_code == 409


async def test_the_email_is_normalized(client, session, admin_token):
    response = await client.post(
        USERS, json={**NEW_ADMIN, "email": "  SOFIA@Example.COM "}, headers=auth(admin_token)
    )

    assert response.json()["email"] == "sofia@example.com"
