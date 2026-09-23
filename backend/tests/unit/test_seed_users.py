import pytest
from sqlalchemy import func, select

from app.core.config import settings
from app.core.enums import AuthProvider, Role, UserStatus, VehicleType
from app.core.security import verify_password
from app.db.seed import (
    TEST_ADMIN,
    TEST_CUSTOMER,
    TEST_DELIVERY,
    run_seed,
    seed_admin_from_env,
    seed_test_users,
)
from app.models import Cart, CustomerBalance, User
from app.repositories.user_repository import UserRepository

TEST_EMAILS = {TEST_CUSTOMER["email"], TEST_ADMIN["email"], TEST_DELIVERY["email"]}


def emails_in(session) -> set[str]:
    return {u.email for u in session.scalars(select(User)).all()}


# ---------- usuarios de prueba (desarrollo) ----------


def test_it_creates_the_three_test_users(session):
    seed_test_users(session)

    assert emails_in(session) == TEST_EMAILS


def test_the_roles_are_the_expected_ones(session):
    seed_test_users(session)

    by_email = {u.email: u.role for u in session.scalars(select(User)).all()}
    assert by_email[TEST_CUSTOMER["email"]] == Role.CUSTOMER
    assert by_email[TEST_ADMIN["email"]] == Role.ADMIN
    assert by_email[TEST_DELIVERY["email"]] == Role.DELIVERY


def test_running_it_twice_does_not_duplicate(session):
    seed_test_users(session)
    seed_test_users(session)

    assert session.scalar(select(func.count()).select_from(User)) == 3


def test_the_second_run_creates_nothing(session):
    seed_test_users(session)

    assert seed_test_users(session) == []


def test_the_documented_passwords_really_work(session):
    """Si el seed y `Usuarios.md` se desincronizan, nadie puede entrar."""
    seed_test_users(session)

    users = UserRepository(session)
    for data in (TEST_CUSTOMER, TEST_ADMIN, TEST_DELIVERY):
        user = users.get_by_email(data["email"])
        assert verify_password(data["password"], user.password_hash), data["email"]


def test_the_test_customer_gets_a_cart_and_a_balance(session):
    seed_test_users(session)

    customer = UserRepository(session).get_by_email(TEST_CUSTOMER["email"])
    assert customer.cart is not None
    assert customer.balance.balance == 0


def test_the_test_delivery_gets_its_profile(session):
    seed_test_users(session)

    delivery = UserRepository(session).get_by_email(TEST_DELIVERY["email"])
    assert delivery.profile.vehicle_type == VehicleType.MOTO.value
    assert delivery.profile.capacity == 4


def test_staff_do_not_get_a_cart_or_a_balance(session):
    seed_test_users(session)

    assert len(session.scalars(select(Cart)).all()) == 1  # solo el cliente
    assert len(session.scalars(select(CustomerBalance)).all()) == 1


def test_every_test_user_is_active_with_a_local_provider(session):
    seed_test_users(session)

    for user in session.scalars(select(User)).all():
        assert user.status == UserStatus.ACTIVE
        assert [p.provider for p in user.auth_providers] == [AuthProvider.LOCAL]


# ---------- producción ----------


def test_it_creates_no_test_users_in_production(session, monkeypatch):
    """Sus contraseñas están en un repositorio público: crearlas en producción
    sería dejar un admin con contraseña conocida por cualquiera."""
    monkeypatch.setattr(settings, "app_env", "production")

    assert seed_test_users(session) == []
    assert session.scalars(select(User)).all() == []


def test_it_warns_when_it_skips_them(session, monkeypatch, caplog):
    monkeypatch.setattr(settings, "app_env", "production")

    with caplog.at_level("WARNING"):
        seed_test_users(session)

    assert "producción" in caplog.text


# ---------- admin inicial desde variables de entorno ----------


@pytest.fixture()
def env_admin(monkeypatch):
    monkeypatch.setattr(settings, "seed_admin_email", "jefe@morficenter.com")
    monkeypatch.setattr(settings, "seed_admin_password", "clave-real-1234")


def test_it_creates_the_first_admin_from_env(session, env_admin):
    """Sin esto no habría forma de crear el primer admin en producción: crear
    usuarios exige ya ser admin."""
    admin = seed_admin_from_env(session)

    assert admin is not None
    assert admin.role == Role.ADMIN
    assert admin.email == "jefe@morficenter.com"
    assert verify_password("clave-real-1234", admin.password_hash)


def test_the_env_admin_also_works_in_production(session, env_admin, monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")

    assert seed_admin_from_env(session) is not None


def test_the_env_admin_is_idempotent(session, env_admin):
    seed_admin_from_env(session)

    assert seed_admin_from_env(session) is None
    assert session.scalar(select(func.count()).select_from(User)) == 1


def test_without_env_variables_no_admin_is_created(session):
    assert seed_admin_from_env(session) is None
    assert session.scalars(select(User)).all() == []


def test_the_env_admin_can_be_authenticated(session, env_admin):
    from app.services.auth_service import AuthService

    seed_admin_from_env(session)

    user = AuthService(session).authenticate(
        email="jefe@morficenter.com", password="clave-real-1234"
    )
    assert user.role == Role.ADMIN


# ---------- run_seed completo ----------


def test_run_seed_creates_everything_in_development(session, env_admin):
    run_seed(session)

    assert emails_in(session) == TEST_EMAILS | {"jefe@morficenter.com"}


def test_run_seed_is_idempotent(session, env_admin):
    run_seed(session)
    run_seed(session)

    assert session.scalar(select(func.count()).select_from(User)) == 4


def test_run_seed_in_production_only_creates_the_env_admin(session, env_admin, monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")

    run_seed(session)

    assert emails_in(session) == {"jefe@morficenter.com"}
