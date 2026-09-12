"""Modelos `User`, `UserAuthProvider`, `UserProfile` (`03_Roadmap.md` T-1.2.1)."""

import datetime as dt

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.enums import AuthProvider, DriverStatus, Role, UserStatus, VehicleType
from app.models.user import User, UserAuthProvider, UserProfile


def _make_user(session, **overrides):
    defaults = {
        "first_name": "Gustavo",
        "last_name": "Pérez",
        "email": "gustavo@morficenter.test",
    }
    user = User(**{**defaults, **overrides})
    session.add(user)
    session.commit()
    return user


def test_create_and_read_user(session):
    user = _make_user(session, phone="+54 11 4444-5555", password_hash="hash-fake")

    fetched = session.get(User, user.id)
    assert fetched is not None
    assert fetched.email == "gustavo@morficenter.test"
    assert fetched.first_name == "Gustavo"
    assert fetched.phone == "+54 11 4444-5555"


def test_user_defaults_role_and_status(session):
    user = _make_user(session)
    fetched = session.get(User, user.id)
    assert fetched.role == Role.CUSTOMER
    assert fetched.status == UserStatus.ACTIVE
    assert fetched.password_hash is None  # opcional (solo login externo)


def test_user_timestamps_are_utc_and_present(session):
    user = _make_user(session)
    fetched = session.get(User, user.id)
    assert isinstance(fetched.created_at, dt.datetime)
    assert fetched.created_at.tzinfo is dt.UTC
    assert isinstance(fetched.updated_at, dt.datetime)


def test_email_must_be_unique(session):
    _make_user(session, email="dup@morficenter.test")
    session.add(User(first_name="Otro", last_name="Usuario", email="dup@morficenter.test"))
    with pytest.raises(IntegrityError):
        session.commit()


def test_role_check_constraint_rejects_invalid_value(session):
    # SQLite valida el CHECK al ejecutar el statement, no recién al commitear.
    user = _make_user(session)
    with pytest.raises(IntegrityError):
        session.execute(text("UPDATE users SET role = 'HACKER' WHERE id = :id"), {"id": user.id})
    session.rollback()


def test_user_auth_provider_link_and_relationship(session):
    user = _make_user(session, email="google@morficenter.test", password_hash=None)
    provider = UserAuthProvider(
        user_id=user.id, provider=AuthProvider.GOOGLE, provider_uid="sub-123"
    )
    session.add(provider)
    session.commit()

    session.refresh(user)
    assert len(user.auth_providers) == 1
    assert user.auth_providers[0].provider == AuthProvider.GOOGLE
    assert user.auth_providers[0].provider_uid == "sub-123"
    assert user.auth_providers[0].linked_at.tzinfo is dt.UTC


def test_two_local_providers_with_null_uid_do_not_collide(session):
    # UNIQUE(provider, provider_uid): en SQLite cada NULL es distinto, así que
    # dos usuarios pueden tener un provider 'local' sin provider_uid cada uno.
    u1 = _make_user(session, email="a@morficenter.test")
    u2 = _make_user(session, email="b@morficenter.test")
    session.add_all(
        [
            UserAuthProvider(user_id=u1.id, provider=AuthProvider.LOCAL, provider_uid=None),
            UserAuthProvider(user_id=u2.id, provider=AuthProvider.LOCAL, provider_uid=None),
        ]
    )
    session.commit()  # no debe lanzar


def test_duplicate_google_uid_is_rejected(session):
    u1 = _make_user(session, email="a2@morficenter.test")
    u2 = _make_user(session, email="b2@morficenter.test")
    session.add(UserAuthProvider(user_id=u1.id, provider=AuthProvider.GOOGLE, provider_uid="sub-x"))
    session.commit()
    session.add(UserAuthProvider(user_id=u2.id, provider=AuthProvider.GOOGLE, provider_uid="sub-x"))
    with pytest.raises(IntegrityError):
        session.commit()


def test_user_profile_defaults_and_relationship(session):
    user = _make_user(session, email="delivery@morficenter.test")
    profile = UserProfile(
        user_id=user.id, vehicle_type=VehicleType.MOTO, driver_status=DriverStatus.DISPONIBLE
    )
    session.add(profile)
    session.commit()

    session.refresh(user)
    assert user.profile is not None
    assert user.profile.vehicle_type == VehicleType.MOTO
    assert user.profile.driver_status == DriverStatus.DISPONIBLE
    assert user.profile.capacity is None
    assert user.profile.updated_at.tzinfo is dt.UTC


def test_deleting_user_cascades_to_provider_and_profile(session):
    user = _make_user(session, email="cascada@morficenter.test")
    session.add(UserAuthProvider(user_id=user.id, provider=AuthProvider.LOCAL))
    session.add(UserProfile(user_id=user.id, notes="test"))
    session.commit()

    session.delete(user)
    session.commit()

    assert session.query(UserAuthProvider).filter_by(user_id=user.id).count() == 0
    assert session.get(UserProfile, user.id) is None
