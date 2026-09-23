from typing import Annotated

import pytest
from fastapi import Depends

from app.api.deps import AdminUser, DeliveryUser, LoggedInUser, require_role
from app.core.enums import Role, UserStatus
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models import User
from app.repositories.user_repository import UserRepository

ADMIN_ONLY = "/api/v1/_test/solo-admin"
DELIVERY_ONLY = "/api/v1/_test/solo-delivery"
LOGGED_IN = "/api/v1/_test/logueado"
STAFF_ONLY = "/api/v1/_test/staff"


@pytest.fixture(autouse=True)
def role_routes():
    """Endpoints mínimos para probar la dependencia; los reales llegan en las
    fases siguientes (admin de usuarios, app del repartidor, etc.)."""

    @app.get(ADMIN_ONLY)
    def _admin(user: AdminUser) -> dict:
        return {"role": user.role}

    @app.get(DELIVERY_ONLY)
    def _delivery(user: DeliveryUser) -> dict:
        return {"role": user.role}

    @app.get(LOGGED_IN)
    def _logged_in(user: LoggedInUser) -> dict:
        return {"role": user.role}

    @app.get(STAFF_ONLY)
    def _staff(user: Annotated[User, Depends(require_role(Role.ADMIN, Role.DELIVERY))]) -> dict:
        return {"role": user.role}

    yield
    test_paths = {ADMIN_ONLY, DELIVERY_ONLY, LOGGED_IN, STAFF_ONLY}
    app.router.routes = [r for r in app.router.routes if getattr(r, "path", "") not in test_paths]


@pytest.fixture()
def token_for(session):
    def make(role: Role, status: UserStatus = UserStatus.ACTIVE) -> str:
        user = UserRepository(session).create(
            first_name="Test",
            last_name=role.value.title(),
            email=f"{role.value.lower()}@example.com",
            password_hash=hash_password("secreta123"),
            role=role,
            status=status,
        )
        session.flush()
        return create_access_token(user)

    return make


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_admin_can_enter_an_admin_endpoint(client, token_for):
    response = await client.get(ADMIN_ONLY, headers=auth(token_for(Role.ADMIN)))

    assert response.status_code == 200
    assert response.json()["role"] == Role.ADMIN.value


@pytest.mark.parametrize("role", [Role.CUSTOMER, Role.DELIVERY])
async def test_other_roles_get_403_on_an_admin_endpoint(client, token_for, role):
    response = await client.get(ADMIN_ONLY, headers=auth(token_for(role)))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


async def test_delivery_can_enter_a_delivery_endpoint(client, token_for):
    response = await client.get(DELIVERY_ONLY, headers=auth(token_for(Role.DELIVERY)))

    assert response.status_code == 200


async def test_an_admin_is_not_automatically_a_delivery(client, token_for):
    """No hay jerarquía de roles: ADMIN no entra a las pantallas del repartidor
    por ser admin — si alguna vez hace falta, se agrega explícitamente."""
    response = await client.get(DELIVERY_ONLY, headers=auth(token_for(Role.ADMIN)))

    assert response.status_code == 403


@pytest.mark.parametrize("role", [Role.CUSTOMER, Role.ADMIN, Role.DELIVERY])
async def test_require_role_without_arguments_allows_any_logged_in_user(client, token_for, role):
    """Las pantallas de cliente se gatean con "cualquiera logueado", no con
    CUSTOMER: un admin también puede querer pedir comida (RN-33, T-1.11.4)."""
    response = await client.get(LOGGED_IN, headers=auth(token_for(role)))

    assert response.status_code == 200


async def test_several_allowed_roles_work(client, token_for):
    admin = await client.get(STAFF_ONLY, headers=auth(token_for(Role.ADMIN)))
    delivery = await client.get(STAFF_ONLY, headers=auth(token_for(Role.DELIVERY)))
    customer = await client.get(STAFF_ONLY, headers=auth(token_for(Role.CUSTOMER)))

    assert admin.status_code == 200
    assert delivery.status_code == 200
    assert customer.status_code == 403


@pytest.mark.parametrize("path", [ADMIN_ONLY, DELIVERY_ONLY, LOGGED_IN, STAFF_ONLY])
async def test_without_a_session_it_is_401_not_403(client, path):
    """401 (no sé quién sos) y 403 (sé quién sos y no podés) son distintos: el
    front redirige al login solo en el primer caso."""
    response = await client.get(path)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"


async def test_a_suspended_admin_cannot_enter(client, token_for):
    token = token_for(Role.ADMIN, status=UserStatus.SUSPENDED)

    response = await client.get(ADMIN_ONLY, headers=auth(token))

    assert response.status_code == 403
