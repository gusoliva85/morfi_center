import pytest

from app.core.enums import AuthProvider, Role, UserStatus
from app.core.errors import ConflictError
from app.core.security import verify_password
from app.models import Cart, CustomerBalance
from app.services.auth_service import AuthService

PASSWORD = "secreta123"


@pytest.fixture()
def service(session) -> AuthService:
    return AuthService(session)


def register(service: AuthService, **overrides):
    data = {
        "first_name": "Ana",
        "last_name": "Pérez",
        "email": "ana@example.com",
        "password": PASSWORD,
    }
    data.update(overrides)
    return service.register(**data)


def test_register_creates_an_active_customer(service):
    user = register(service)

    assert user.id is not None
    assert user.role == Role.CUSTOMER
    assert user.status == UserStatus.ACTIVE
    assert user.first_name == "Ana"
    assert user.email == "ana@example.com"


def test_register_stores_the_password_hashed_never_in_plain_text(service):
    user = register(service)

    assert user.password_hash != PASSWORD
    assert verify_password(PASSWORD, user.password_hash)


def test_register_links_the_local_provider(service):
    user = register(service)

    assert [p.provider for p in user.auth_providers] == [AuthProvider.LOCAL]
    assert user.auth_providers[0].provider_uid is None


def test_register_creates_the_cart_and_the_balance_in_zero(service, session):
    user = register(service)

    assert user.cart is not None
    assert user.balance is not None
    assert user.balance.balance == 0
    assert session.get(Cart, user.cart.id) is not None
    assert session.get(CustomerBalance, user.id) is not None


def test_register_normalizes_the_email(service):
    user = register(service, email="  Ana@Example.COM ")

    assert user.email == "ana@example.com"


def test_register_trims_names_and_phone(service):
    user = register(service, first_name="  Ana  ", last_name=" Pérez ", phone=" 1155551234 ")

    assert user.first_name == "Ana"
    assert user.last_name == "Pérez"
    assert user.phone == "1155551234"


def test_phone_is_optional(service):
    user = register(service)

    assert user.phone is None


def test_empty_phone_is_stored_as_null_not_as_empty_string(service):
    user = register(service, phone="")

    assert user.phone is None


def test_registering_a_duplicated_email_raises_conflict(service):
    register(service)

    with pytest.raises(ConflictError):
        register(service, first_name="Otra")


def test_duplicated_email_is_detected_ignoring_case_and_spaces(service):
    register(service, email="ana@example.com")

    with pytest.raises(ConflictError):
        register(service, email="  ANA@Example.com  ")


def test_a_failed_duplicate_does_not_create_a_second_user(service, session):
    register(service)

    with pytest.raises(ConflictError):
        register(service)

    from sqlalchemy import func, select

    from app.models import User

    assert session.scalar(select(func.count()).select_from(User)) == 1


def test_a_simultaneous_duplicate_is_a_conflict_not_a_crash(service, monkeypatch):
    """Dos altas a la vez con el mismo email: ambas pasan el chequeo previo y
    una choca contra el UNIQUE de la base. Tiene que salir ConflictError
    (409), no un IntegrityError sin manejar (500)."""
    register(service)
    monkeypatch.setattr(service.users, "get_by_email", lambda email: None)

    with pytest.raises(ConflictError):
        register(service)


def test_two_different_customers_can_register(service):
    first = register(service)
    second = register(service, email="juan@example.com", first_name="Juan")

    assert first.id != second.id
    assert second.cart is not None
    assert second.balance is not None
