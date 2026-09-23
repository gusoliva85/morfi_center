import pytest

from app.core.enums import AuthProvider, Role, UserStatus
from app.core.errors import ForbiddenError, NotAuthenticatedError
from app.services.auth_service import INVALID_CREDENTIALS, AuthService

PASSWORD = "secreta123"
EMAIL = "ana@example.com"


@pytest.fixture()
def service(session) -> AuthService:
    return AuthService(session)


@pytest.fixture()
def customer(service):
    return service.register(first_name="Ana", last_name="Pérez", email=EMAIL, password=PASSWORD)


def test_authenticate_returns_the_user_with_the_right_credentials(service, customer):
    assert service.authenticate(email=EMAIL, password=PASSWORD) is customer


def test_authenticate_accepts_the_email_in_any_case(service, customer):
    assert service.authenticate(email="  ANA@Example.COM ", password=PASSWORD) is customer


def test_a_wrong_password_is_rejected(service, customer):
    with pytest.raises(NotAuthenticatedError):
        service.authenticate(email=EMAIL, password="otra-cosa-123")


def test_an_unknown_email_is_rejected(service):
    with pytest.raises(NotAuthenticatedError):
        service.authenticate(email="nadie@example.com", password=PASSWORD)


def test_unknown_email_and_wrong_password_give_the_exact_same_message(service, customer):
    """No debe poder deducirse si el email existe a partir del error."""
    with pytest.raises(NotAuthenticatedError) as unknown_email:
        service.authenticate(email="nadie@example.com", password=PASSWORD)
    with pytest.raises(NotAuthenticatedError) as wrong_password:
        service.authenticate(email=EMAIL, password="otra-cosa-123")

    assert unknown_email.value.message == wrong_password.value.message == INVALID_CREDENTIALS


def test_an_empty_password_is_rejected(service, customer):
    with pytest.raises(NotAuthenticatedError):
        service.authenticate(email=EMAIL, password="")


def test_a_suspended_user_cannot_log_in(service, customer, session):
    customer.status = UserStatus.SUSPENDED
    session.flush()

    with pytest.raises(ForbiddenError):
        service.authenticate(email=EMAIL, password=PASSWORD)


def test_an_inactive_user_cannot_log_in(service, customer, session):
    customer.status = UserStatus.INACTIVE
    session.flush()

    with pytest.raises(ForbiddenError):
        service.authenticate(email=EMAIL, password=PASSWORD)


def test_a_suspended_user_with_a_wrong_password_gets_the_generic_error(service, customer, session):
    """El aviso de cuenta deshabilitada solo lo ve quien acertó la contraseña:
    si no, serviría para descubrir qué emails están registrados."""
    customer.status = UserStatus.SUSPENDED
    session.flush()

    with pytest.raises(NotAuthenticatedError):
        service.authenticate(email=EMAIL, password="otra-cosa-123")


def test_a_google_only_account_cannot_log_in_with_a_password(service, session):
    """Cuenta sin contraseña (solo Google): no debe explotar ni dejar entrar
    con cualquier contraseña — sale el error genérico."""
    google_user = service.users.create(
        first_name="Juan", last_name="Gómez", email="juan@example.com", password_hash=None
    )
    service.users.link_provider(google_user, AuthProvider.GOOGLE, provider_uid="google-sub-1")
    session.flush()

    with pytest.raises(NotAuthenticatedError):
        service.authenticate(email="juan@example.com", password=PASSWORD)


def test_staff_can_authenticate_too(service, session):
    from app.core.security import hash_password

    admin = service.users.create(
        first_name="Admin",
        last_name="Morfi",
        email="admin@example.com",
        password_hash=hash_password(PASSWORD),
        role=Role.ADMIN,
    )
    session.flush()

    assert service.authenticate(email="admin@example.com", password=PASSWORD) is admin
