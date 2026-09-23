import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.core.enums import AuthProvider, DriverStatus, Role, UserStatus
from app.core.timezone import UTC
from app.models import User, UserAuthProvider, UserProfile


def make_user(**overrides) -> User:
    data = {"first_name": "Ana", "last_name": "Pérez", "email": "ana@example.com"}
    data.update(overrides)
    return User(**data)


def test_create_user_and_read_it_back(session):
    session.add(make_user(phone="1155551234", password_hash="hash"))
    session.commit()
    session.expire_all()

    user = session.scalars(select(User)).one()
    assert user.id is not None
    assert user.first_name == "Ana"
    assert user.email == "ana@example.com"
    assert user.phone == "1155551234"
    assert user.password_hash == "hash"


def test_user_defaults_to_active_customer(session):
    session.add(make_user())
    session.commit()
    session.expire_all()

    user = session.scalars(select(User)).one()
    assert user.role == Role.CUSTOMER
    assert user.status == UserStatus.ACTIVE
    assert user.phone is None
    assert user.password_hash is None


def test_timestamps_are_set_automatically_in_utc(session):
    session.add(make_user())
    session.commit()
    session.expire_all()

    user = session.scalars(select(User)).one()
    assert user.created_at.tzinfo is not None
    assert user.created_at.utcoffset().total_seconds() == 0
    assert user.updated_at.tzinfo is not None


def test_updated_at_changes_on_update_but_created_at_does_not(session):
    user = make_user()
    session.add(user)
    session.commit()
    created_at, first_updated_at = user.created_at, user.updated_at

    user.phone = "1100000000"
    session.commit()
    session.expire_all()

    reloaded = session.get(User, user.id)
    assert reloaded.created_at == created_at
    assert reloaded.updated_at > first_updated_at


def test_role_is_stored_as_enum_value_text(session):
    session.add(make_user(role=Role.DELIVERY))
    session.commit()

    raw = session.execute(text("SELECT role FROM users")).scalar_one()
    assert raw == "DELIVERY"


def test_duplicate_email_is_rejected(session):
    session.add(make_user())
    session.commit()

    session.add(make_user(first_name="Otra"))
    with pytest.raises(IntegrityError):
        session.commit()


def test_invalid_role_is_rejected_by_check_constraint(session):
    session.add(make_user())
    session.commit()

    with pytest.raises(IntegrityError):
        session.execute(text("UPDATE users SET role = 'HACKER'"))


def test_auth_provider_local_and_google_link_to_user(session):
    user = make_user()
    user.auth_providers.append(UserAuthProvider(provider=AuthProvider.LOCAL))
    user.auth_providers.append(
        UserAuthProvider(provider=AuthProvider.GOOGLE, provider_uid="google-sub-123")
    )
    session.add(user)
    session.commit()
    session.expire_all()

    providers = session.get(User, user.id).auth_providers
    assert {p.provider for p in providers} == {AuthProvider.LOCAL, AuthProvider.GOOGLE}
    assert all(p.linked_at.tzinfo is not None for p in providers)


def test_same_google_account_cannot_link_to_two_users(session):
    first = make_user()
    first.auth_providers.append(UserAuthProvider(provider=AuthProvider.GOOGLE, provider_uid="g1"))
    second = make_user(email="otro@example.com")
    second.auth_providers.append(UserAuthProvider(provider=AuthProvider.GOOGLE, provider_uid="g1"))
    session.add_all([first, second])

    with pytest.raises(IntegrityError):
        session.commit()


def test_many_local_providers_with_null_uid_are_allowed(session):
    for email in ("a@example.com", "b@example.com"):
        user = make_user(email=email)
        user.auth_providers.append(UserAuthProvider(provider=AuthProvider.LOCAL))
        session.add(user)
    session.commit()

    assert len(session.scalars(select(UserAuthProvider)).all()) == 2


def test_delivery_profile_is_one_to_one_with_user(session):
    user = make_user(role=Role.DELIVERY)
    user.profile = UserProfile(
        vehicle_type="moto", capacity=4, driver_status=DriverStatus.DISPONIBLE, notes="turno tarde"
    )
    session.add(user)
    session.commit()
    session.expire_all()

    profile = session.get(User, user.id).profile
    assert profile.vehicle_type == "moto"
    assert profile.capacity == 4
    assert profile.driver_status == DriverStatus.DISPONIBLE
    assert profile.updated_at.tzinfo is not None
    assert profile.user_id == user.id


def test_invalid_vehicle_type_is_rejected(session):
    user = make_user(role=Role.DELIVERY)
    user.profile = UserProfile(vehicle_type="cohete")
    session.add(user)

    with pytest.raises(IntegrityError):
        session.commit()


def test_deleting_user_cascades_to_providers_and_profile(session):
    user = make_user(role=Role.DELIVERY)
    user.auth_providers.append(UserAuthProvider(provider=AuthProvider.LOCAL))
    user.profile = UserProfile(vehicle_type="bici")
    session.add(user)
    session.commit()

    session.delete(user)
    session.commit()

    assert session.scalars(select(UserAuthProvider)).all() == []
    assert session.scalars(select(UserProfile)).all() == []


def test_utc_datetime_rejects_naive_datetimes(session):
    from datetime import datetime

    session.add(make_user(created_at=datetime(2026, 9, 10, 12, 0)))
    with pytest.raises(Exception, match="tz-aware"):
        session.commit()


def test_utc_datetime_normalizes_other_timezones_to_utc(session):
    from datetime import datetime, timedelta, timezone

    ba = timezone(timedelta(hours=-3))
    session.add(make_user(created_at=datetime(2026, 9, 10, 12, 0, tzinfo=ba)))
    session.commit()
    session.expire_all()

    user = session.scalars(select(User)).one()
    assert user.created_at == datetime(2026, 9, 10, 15, 0, tzinfo=UTC)
