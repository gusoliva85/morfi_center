import pytest
from sqlalchemy import select

from app.core.enums import Role, UserStatus
from app.core.security import create_access_token, hash_password
from app.models import User
from app.repositories.user_repository import UserRepository

PROFILE = "/api/v1/users/me/profile"
REGISTER = "/api/v1/auth/register"
ME = "/api/v1/auth/me"

ACCOUNT = {
    "first_name": "Ana",
    "last_name": "Pérez",
    "email": "ana@example.com",
    "password": "secreta123",
    "phone": "1155551234",
}


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
async def token(client):
    registered = await client.post(REGISTER, json=ACCOUNT)
    return registered.json()["access_token"]


async def test_changing_the_phone_persists(client, session, token):
    response = await client.patch(PROFILE, json={"phone": "1199998888"}, headers=auth(token))

    assert response.status_code == 200
    assert response.json()["phone"] == "1199998888"
    session.expire_all()
    assert session.scalars(select(User)).one().phone == "1199998888"


async def test_changing_the_names_persists(client, session, token):
    response = await client.patch(
        PROFILE, json={"first_name": "Juan", "last_name": "Gómez"}, headers=auth(token)
    )

    assert response.status_code == 200
    session.expire_all()
    user = session.scalars(select(User)).one()
    assert (user.first_name, user.last_name) == ("Juan", "Gómez")


async def test_a_partial_update_does_not_erase_the_other_fields(client, token):
    response = await client.patch(PROFILE, json={"first_name": "Juan"}, headers=auth(token))

    body = response.json()
    assert body["first_name"] == "Juan"
    assert body["last_name"] == "Pérez"
    assert body["phone"] == "1155551234"


async def test_sending_phone_null_clears_it(client, token):
    response = await client.patch(PROFILE, json={"phone": None}, headers=auth(token))

    assert response.status_code == 200
    assert response.json()["phone"] is None


async def test_an_empty_body_changes_nothing(client, token):
    response = await client.patch(PROFILE, json={}, headers=auth(token))

    assert response.status_code == 200
    assert response.json()["first_name"] == "Ana"
    assert response.json()["phone"] == "1155551234"


async def test_the_response_has_the_same_shape_as_auth_me(client, token):
    updated = await client.patch(PROFILE, json={"phone": "1122"}, headers=auth(token))
    me = await client.get(ME, headers=auth(token))

    assert updated.json() == me.json()


async def test_the_email_is_not_editable_here(client, session, token):
    response = await client.patch(PROFILE, json={"email": "otro@example.com"}, headers=auth(token))

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    session.expire_all()
    assert session.scalars(select(User)).one().email == ACCOUNT["email"]


async def test_the_role_is_not_editable_here(client, session, token):
    response = await client.patch(PROFILE, json={"role": Role.ADMIN.value}, headers=auth(token))

    assert response.status_code == 422
    session.expire_all()
    assert session.scalars(select(User)).one().role == Role.CUSTOMER


async def test_the_password_is_not_editable_here(client, token):
    response = await client.patch(PROFILE, json={"password": "otra-clave-9"}, headers=auth(token))

    assert response.status_code == 422


@pytest.mark.parametrize("field", ["first_name", "last_name"])
@pytest.mark.parametrize("blank", ["", "   ", None])
async def test_a_blank_name_is_rejected(client, token, field, blank):
    response = await client.patch(PROFILE, json={field: blank}, headers=auth(token))

    assert response.status_code == 422
    assert field in [f["field"] for f in response.json()["error"]["details"]["fields"]]


async def test_names_are_trimmed(client, token):
    response = await client.patch(
        PROFILE, json={"first_name": "  Juan  ", "phone": " 1122 "}, headers=auth(token)
    )

    assert response.json()["first_name"] == "Juan"
    assert response.json()["phone"] == "1122"


async def test_without_a_token_it_is_401(client):
    response = await client.patch(PROFILE, json={"phone": "1122"})

    assert response.status_code == 401


async def test_a_suspended_user_cannot_edit(client, session, token):
    session.scalars(select(User)).one().status = UserStatus.SUSPENDED
    session.flush()

    response = await client.patch(PROFILE, json={"phone": "1122"}, headers=auth(token))

    assert response.status_code == 403


async def test_it_only_edits_the_user_of_the_session(client, session, token):
    other = UserRepository(session).create(
        first_name="Juan",
        last_name="Gómez",
        email="juan@example.com",
        password_hash=hash_password("secreta123"),
        phone="1100000000",
    )
    session.flush()

    await client.patch(PROFILE, json={"phone": "1199998888"}, headers=auth(token))

    session.expire_all()
    assert session.get(User, other.id).phone == "1100000000"


async def test_staff_can_edit_their_profile_too(client, session):
    admin = UserRepository(session).create(
        first_name="Admin",
        last_name="Morfi",
        email="admin@example.com",
        password_hash=hash_password("secreta123"),
        role=Role.ADMIN,
    )
    session.flush()

    response = await client.patch(
        PROFILE, json={"phone": "1155550000"}, headers=auth(create_access_token(admin))
    )

    assert response.status_code == 200
    assert response.json()["phone"] == "1155550000"
    assert response.json()["balance"] == 0
