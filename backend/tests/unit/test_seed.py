"""Esqueleto de seed (`03_Roadmap.md` T-0.3.4), usuarios de prueba (T-1.10.1)
y `system_settings` (T-2.1.4).

`test_run_seed_*` y `test_seed_module_runs_as_script` corren contra la DB de
**desarrollo real** (`session_scope()` / el script tal cual se invoca) a
propósito: es justo lo que pide la prueba oficial de T-1.10.1 (`python -m
app.db.seed` deja los 3 usuarios; correr dos veces no duplica). El resto de
los tests de `seed_users` usan la `session` en memoria de siempre, para
verificar la lógica sin tocar la DB real.
"""

import subprocess
import sys
from pathlib import Path

from sqlalchemy import MetaData, String, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from app.core.enums import Role
from app.core.security import verify_password
from app.db.base import NAMING_CONVENTION
from app.db.seed import (
    SEED_ADMIN_EMAIL,
    SEED_ADMIN_PASSWORD,
    SEED_CUSTOMER_EMAIL,
    SEED_CUSTOMER_PASSWORD,
    SEED_DELIVERY_EMAIL,
    SEED_DELIVERY_PASSWORD,
    get_or_create,
    run_seed,
    seed_settings,
    seed_users,
)
from app.db.session import build_engine, session_scope
from app.models.settings import SystemSetting
from app.models.user import User, UserProfile
from app.repositories.settings_repository import SettingsRepository
from app.repositories.user_repository import UserRepository
from app.services.settings_service import SETTINGS_DEFAULTS, SettingKey

BACKEND_DIR = Path(__file__).resolve().parents[2]
_SEED_EMAILS = [SEED_ADMIN_EMAIL, SEED_CUSTOMER_EMAIL, SEED_DELIVERY_EMAIL]


def test_run_seed_does_not_raise():
    with session_scope() as session:
        run_seed(session)


def test_run_seed_leaves_the_three_test_users():
    with session_scope() as session:
        run_seed(session)
        repo = UserRepository(session)
        assert repo.get_by_email(SEED_ADMIN_EMAIL) is not None
        assert repo.get_by_email(SEED_CUSTOMER_EMAIL) is not None
        assert repo.get_by_email(SEED_DELIVERY_EMAIL) is not None


def test_run_seed_twice_does_not_duplicate_users():
    with session_scope() as session:
        run_seed(session)
        run_seed(session)
        count = session.scalar(
            select(func.count()).select_from(User).where(User.email.in_(_SEED_EMAILS))
        )
        assert count == 3


def test_run_seed_leaves_every_known_setting_key():
    with session_scope() as session:
        run_seed(session)
        repo = SettingsRepository(session)
        for key in SETTINGS_DEFAULTS:
            assert repo.get(key.value) is not None


def test_seed_module_runs_as_script():
    result = subprocess.run(
        [sys.executable, "-m", "app.db.seed"],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr


# ── seed_users (DB en memoria, aislada por test) ──────────
def test_seed_users_creates_admin_customer_and_delivery(session: Session):
    seed_users(session)
    repo = UserRepository(session)

    admin = repo.get_by_email(SEED_ADMIN_EMAIL)
    customer = repo.get_by_email(SEED_CUSTOMER_EMAIL)
    delivery = repo.get_by_email(SEED_DELIVERY_EMAIL)

    assert admin is not None and admin.role == Role.ADMIN
    assert customer is not None and customer.role == Role.CUSTOMER
    assert delivery is not None and delivery.role == Role.DELIVERY


def test_seed_users_passwords_match_the_documented_credentials(session: Session):
    seed_users(session)
    repo = UserRepository(session)

    assert verify_password(SEED_ADMIN_PASSWORD, repo.get_by_email(SEED_ADMIN_EMAIL).password_hash)
    assert verify_password(
        SEED_CUSTOMER_PASSWORD, repo.get_by_email(SEED_CUSTOMER_EMAIL).password_hash
    )
    assert verify_password(
        SEED_DELIVERY_PASSWORD, repo.get_by_email(SEED_DELIVERY_EMAIL).password_hash
    )


def test_seed_users_customer_has_cart_and_balance(session: Session):
    seed_users(session)
    customer = UserRepository(session).get_by_email(SEED_CUSTOMER_EMAIL)
    session.refresh(customer)
    assert customer.cart is not None
    assert customer.balance is not None
    assert customer.balance.balance == 0


def test_seed_users_delivery_has_a_vehicle_profile(session: Session):
    seed_users(session)
    delivery = UserRepository(session).get_by_email(SEED_DELIVERY_EMAIL)
    profile = session.scalars(select(UserProfile).where(UserProfile.user_id == delivery.id)).first()
    assert profile is not None
    assert profile.vehicle_type.value == "moto"


def test_seed_users_is_idempotent(session: Session):
    seed_users(session)
    seed_users(session)

    count = session.scalar(
        select(func.count()).select_from(User).where(User.email.in_(_SEED_EMAILS))
    )
    assert count == 3


# ── seed_settings (DB en memoria, aislada por test) ───────
def test_seed_settings_inserts_every_known_key_with_its_default(session: Session):
    seed_settings(session)
    repo = SettingsRepository(session)
    for key, default_value in SETTINGS_DEFAULTS.items():
        assert repo.get(key.value) == default_value


def test_seed_settings_does_not_overwrite_a_value_already_configured(session: Session):
    SettingsRepository(session).set(SettingKey.ORDERS_CODE_PREFIX.value, "YA_CONFIGURADO")
    seed_settings(session)
    assert SettingsRepository(session).get(SettingKey.ORDERS_CODE_PREFIX.value) == "YA_CONFIGURADO"


def test_seed_settings_twice_does_not_duplicate_rows(session: Session):
    seed_settings(session)
    seed_settings(session)
    count = session.scalar(select(func.count()).select_from(SystemSetting))
    assert count == len(SETTINGS_DEFAULTS)


def test_get_or_create_is_idempotent():
    meta = MetaData(naming_convention=NAMING_CONVENTION)

    class LocalBase(DeclarativeBase):
        metadata = meta

    class Tag(LocalBase):
        __tablename__ = "tag"
        id: Mapped[int] = mapped_column(primary_key=True)
        name: Mapped[str] = mapped_column(String(50), unique=True)
        color: Mapped[str] = mapped_column(String(20), default="gray")

    engine = build_engine("sqlite://")
    meta.create_all(engine)

    with Session(engine) as s:
        obj1, created1 = get_or_create(s, Tag, defaults={"color": "red"}, name="promo")
        assert created1 is True
        assert obj1.id is not None and obj1.color == "red"

        obj2, created2 = get_or_create(s, Tag, defaults={"color": "blue"}, name="promo")
        assert created2 is False
        assert obj2.id == obj1.id
        assert obj2.color == "red"  # no se toca lo existente

        assert s.scalar(select(func.count()).select_from(Tag)) == 1
