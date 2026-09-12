"""`AuthService.register`, `.authenticate`, `.refresh_session`,
`.create_staff`, `.login_with_google` y `.request_password_reset`/
`.reset_password` (`03_Roadmap.md` T-1.3.1, T-1.4.1, T-1.4.3, T-1.7.1,
T-1.8.2, T-1.9.1)."""

from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.enums import AuthProvider, Role, UserStatus, VehicleType
from app.core.errors import (
    ConflictError,
    ForbiddenError,
    InvalidInputError,
    NotAuthenticatedError,
    NotFoundError,
)
from app.core.security import (
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    verify_password,
)
from app.core.timezone import now_utc
from app.models.audit import AuditLog
from app.models.user import UserProfile
from app.repositories.token_repository import TokenRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService

VALID = {
    "first_name": "Gustavo",
    "last_name": "Pérez",
    "email": "gustavo@morficenter.test",
    "password": "cliente123",
}


def test_register_creates_user_with_expected_defaults(session):
    user = AuthService(session).register(**VALID)

    assert user.id is not None
    assert user.email == "gustavo@morficenter.test"
    assert user.role == Role.CUSTOMER
    assert user.status == UserStatus.ACTIVE


def test_register_hashes_the_password_not_plain_text(session):
    user = AuthService(session).register(**VALID)

    assert user.password_hash != VALID["password"]
    assert verify_password(VALID["password"], user.password_hash) is True


def test_register_links_a_local_auth_provider(session):
    user = AuthService(session).register(**VALID)
    repo = UserRepository(session)

    session.refresh(user)
    assert len(user.auth_providers) == 1
    assert user.auth_providers[0].provider == AuthProvider.LOCAL
    assert user.auth_providers[0].provider_uid is None
    assert repo.get_by_id(user.id) is not None  # sanity


def test_register_creates_cart_and_zero_balance(session):
    user = AuthService(session).register(**VALID)
    session.refresh(user)

    assert user.cart is not None
    assert user.balance is not None
    assert user.balance.balance == 0


def test_register_normalizes_email_and_phone(session):
    user = AuthService(session).register(
        **{**VALID, "email": "  Gustavo@Morficenter.TEST  ", "phone": "  +54 11 4444-5555  "}
    )
    assert user.email == "gustavo@morficenter.test"
    assert user.phone == "+54 11 4444-5555"


def test_register_duplicate_email_raises_conflict(session):
    AuthService(session).register(**VALID)

    with pytest.raises(ConflictError) as exc:
        AuthService(session).register(**{**VALID, "first_name": "Otro"})
    assert exc.value.details["field"] == "email"


def test_register_duplicate_email_is_case_and_space_insensitive(session):
    AuthService(session).register(**VALID)

    with pytest.raises(ConflictError):
        AuthService(session).register(**{**VALID, "email": "  GUSTAVO@MorfiCenter.test  "})


@pytest.mark.parametrize(
    "overrides",
    [
        {"email": "no-es-un-email"},
        {"first_name": ""},
        {"last_name": "123"},
        {"password": "corta1"},
        {"password": "sinNumero"},
    ],
)
def test_register_invalid_input_raises_and_creates_nothing(session, overrides):
    repo = UserRepository(session)
    with pytest.raises(InvalidInputError):
        AuthService(session).register(**{**VALID, **overrides})

    assert repo.get_by_email(VALID["email"].lower()) is None
    assert repo.list().total == 0


def test_register_does_not_commit_only_flushes(session):
    user = AuthService(session).register(**VALID)
    user_id = user.id

    session.rollback()

    repo = UserRepository(session)
    assert repo.get_by_id(user_id) is None


# ══════════════════════════════════════════════════════════
#  authenticate (T-1.4.1)
# ══════════════════════════════════════════════════════════


def test_authenticate_with_correct_credentials_returns_the_user(session):
    registered = AuthService(session).register(**VALID)

    user = AuthService(session).authenticate(VALID["email"], VALID["password"])
    assert user.id == registered.id


def test_authenticate_is_case_and_space_insensitive_on_email(session):
    AuthService(session).register(**VALID)

    user = AuthService(session).authenticate("  GUSTAVO@MorfiCenter.TEST  ", VALID["password"])
    assert user.email == VALID["email"]


def test_authenticate_wrong_password_raises_generic_not_authenticated(session):
    AuthService(session).register(**VALID)

    with pytest.raises(NotAuthenticatedError) as exc:
        AuthService(session).authenticate(VALID["email"], "contraseña-incorrecta1")
    assert "incorrect" in exc.value.message.lower()


def test_authenticate_unknown_email_raises_the_same_generic_error(session):
    with pytest.raises(NotAuthenticatedError) as exc_unknown:
        AuthService(session).authenticate("no-existe@morficenter.test", "cualquiera123")

    AuthService(session).register(**VALID)
    with pytest.raises(NotAuthenticatedError) as exc_wrong_pw:
        AuthService(session).authenticate(VALID["email"], "otra-mala1")

    # mismo mensaje para "no existe" y "contraseña incorrecta": no se filtra
    # si el email está registrado.
    assert exc_unknown.value.message == exc_wrong_pw.value.message


def test_authenticate_suspended_user_with_right_password_raises_forbidden(session):
    user = AuthService(session).register(**VALID)
    user.status = UserStatus.SUSPENDED
    session.flush()

    with pytest.raises(ForbiddenError):
        AuthService(session).authenticate(VALID["email"], VALID["password"])


def test_authenticate_suspended_user_with_wrong_password_still_generic(session):
    # no debe filtrar "esta cuenta existe y está suspendida" a quien ni
    # siquiera acertó la contraseña.
    user = AuthService(session).register(**VALID)
    user.status = UserStatus.SUSPENDED
    session.flush()

    with pytest.raises(NotAuthenticatedError):
        AuthService(session).authenticate(VALID["email"], "mala-contraseña1")


def test_authenticate_user_without_local_password_is_rejected(session):
    # usuario que solo se registró con Google (sin password_hash): no puede
    # loguearse con contraseña, y el error no debe distinguirse del genérico.
    user = AuthService(session).register(**VALID)
    user.password_hash = None
    session.flush()

    with pytest.raises(NotAuthenticatedError):
        AuthService(session).authenticate(VALID["email"], VALID["password"])


# ══════════════════════════════════════════════════════════
#  refresh_session (T-1.4.3)
# ══════════════════════════════════════════════════════════


def test_refresh_session_with_valid_token_returns_the_owner(session):
    user = AuthService(session).register(**VALID)
    refresh_token, _jti = create_refresh_token(user.id)

    same_user = AuthService(session).refresh_session(refresh_token)
    assert same_user.id == user.id


def test_refresh_session_none_or_empty_raises(session):
    with pytest.raises(NotAuthenticatedError):
        AuthService(session).refresh_session(None)
    with pytest.raises(NotAuthenticatedError):
        AuthService(session).refresh_session("")


def test_refresh_session_malformed_token_raises(session):
    with pytest.raises(NotAuthenticatedError):
        AuthService(session).refresh_session("esto-no-es-un-jwt")


def test_refresh_session_expired_token_raises(session):
    user = AuthService(session).register(**VALID)
    stale = now_utc() - timedelta(days=settings.refresh_token_days + 1)
    refresh_token, _jti = create_refresh_token(user.id, now=stale)

    with pytest.raises(NotAuthenticatedError):
        AuthService(session).refresh_session(refresh_token)


def test_refresh_session_rejects_an_access_token(session):
    user = AuthService(session).register(**VALID)
    access_token = create_access_token(user.id, user.role)

    with pytest.raises(NotAuthenticatedError):
        AuthService(session).refresh_session(access_token)


def test_refresh_session_revokes_the_token_so_it_cannot_be_reused(session):
    user = AuthService(session).register(**VALID)
    refresh_token, jti = create_refresh_token(user.id)

    AuthService(session).refresh_session(refresh_token)  # 1er uso: OK
    assert TokenRepository(session).is_revoked(jti) is True

    with pytest.raises(NotAuthenticatedError):
        AuthService(session).refresh_session(refresh_token)  # reuse: 401


def test_refresh_session_for_deleted_user_raises(session):
    user = AuthService(session).register(**VALID)
    refresh_token, _jti = create_refresh_token(user.id)
    session.delete(user)
    session.flush()

    with pytest.raises(NotAuthenticatedError):
        AuthService(session).refresh_session(refresh_token)


def test_refresh_session_for_suspended_user_raises(session):
    user = AuthService(session).register(**VALID)
    refresh_token, _jti = create_refresh_token(user.id)
    user.status = UserStatus.SUSPENDED
    session.flush()

    with pytest.raises(NotAuthenticatedError):
        AuthService(session).refresh_session(refresh_token)


# ══════════════════════════════════════════════════════════
#  logout (T-1.4.4)
# ══════════════════════════════════════════════════════════


def test_logout_revokes_a_valid_refresh_token(session):
    user = AuthService(session).register(**VALID)
    refresh_token, jti = create_refresh_token(user.id)

    AuthService(session).logout(refresh_token)

    assert TokenRepository(session).is_revoked(jti) is True
    with pytest.raises(NotAuthenticatedError):
        AuthService(session).refresh_session(refresh_token)  # ya no sirve


def test_logout_does_not_raise_without_a_token(session):
    AuthService(session).logout(None)
    AuthService(session).logout("")  # no debe lanzar


def test_logout_does_not_raise_with_a_malformed_token(session):
    AuthService(session).logout("esto-no-es-un-jwt")


def test_logout_does_not_raise_with_an_expired_token(session):
    user = AuthService(session).register(**VALID)
    stale = now_utc() - timedelta(days=settings.refresh_token_days + 1)
    refresh_token, _jti = create_refresh_token(user.id, now=stale)

    AuthService(session).logout(refresh_token)  # no debe lanzar


def test_logout_does_not_raise_with_an_access_token_by_mistake(session):
    user = AuthService(session).register(**VALID)
    access_token = create_access_token(user.id, user.role)

    AuthService(session).logout(access_token)  # tipo incorrecto: se ignora


def test_logout_twice_with_the_same_token_is_idempotent(session):
    user = AuthService(session).register(**VALID)
    refresh_token, jti = create_refresh_token(user.id)

    AuthService(session).logout(refresh_token)
    AuthService(session).logout(refresh_token)  # segunda vez: no debe lanzar
    assert TokenRepository(session).is_revoked(jti) is True


# ── create_staff ──────────────────────────────────────────
STAFF = {
    "first_name": "Ana",
    "last_name": "Gómez",
    "email": "ana@morficenter.test",
}


def test_create_staff_admin_with_explicit_password(session):
    user, temporary_password = AuthService(session).create_staff(
        role=Role.ADMIN, password="admin1234", **STAFF
    )

    assert user.id is not None
    assert user.role == Role.ADMIN
    assert user.status == UserStatus.ACTIVE
    assert verify_password("admin1234", user.password_hash) is True
    assert temporary_password is None  # no se repite lo que ya definió el admin


def test_create_staff_without_password_generates_a_temporary_one(session):
    user, temporary_password = AuthService(session).create_staff(role=Role.ADMIN, **STAFF)

    assert temporary_password is not None
    assert len(temporary_password) >= 8
    assert verify_password(temporary_password, user.password_hash) is True


def test_create_staff_links_a_local_auth_provider(session):
    user, _ = AuthService(session).create_staff(role=Role.ADMIN, **STAFF)
    session.refresh(user)
    assert len(user.auth_providers) == 1
    assert user.auth_providers[0].provider == AuthProvider.LOCAL


def test_create_staff_does_not_issue_tokens_or_create_cart_and_balance(session):
    user, _ = AuthService(session).create_staff(role=Role.ADMIN, **STAFF)
    session.refresh(user)
    assert user.cart is None
    assert user.balance is None


def test_create_staff_delivery_creates_a_user_profile_with_vehicle_data(session):
    user, _ = AuthService(session).create_staff(
        role=Role.DELIVERY, vehicle_type=VehicleType.MOTO, capacity=3, **STAFF
    )

    profile = session.scalars(select(UserProfile).where(UserProfile.user_id == user.id)).first()
    assert profile is not None
    assert profile.vehicle_type == VehicleType.MOTO
    assert profile.capacity == 3


def test_create_staff_admin_does_not_create_a_user_profile(session):
    user, _ = AuthService(session).create_staff(role=Role.ADMIN, **STAFF)

    profile = session.scalars(select(UserProfile).where(UserProfile.user_id == user.id)).first()
    assert profile is None


def test_create_staff_rejects_customer_role(session):
    with pytest.raises(InvalidInputError) as exc:
        AuthService(session).create_staff(role=Role.CUSTOMER, **STAFF)
    assert exc.value.details["field"] == "role"


def test_create_staff_duplicate_email_raises_conflict(session):
    AuthService(session).create_staff(role=Role.ADMIN, **STAFF)
    with pytest.raises(ConflictError):
        AuthService(session).create_staff(role=Role.DELIVERY, **STAFF)


def test_create_staff_invalid_explicit_password_raises(session):
    with pytest.raises(InvalidInputError) as exc:
        AuthService(session).create_staff(role=Role.ADMIN, password="short", **STAFF)
    assert exc.value.details["field"] == "password"


# ── list_users ────────────────────────────────────────────
def test_list_users_delegates_to_the_repository(session):
    AuthService(session).register(**VALID)
    AuthService(session).create_staff(role=Role.ADMIN, **STAFF)

    page = AuthService(session).list_users()
    assert page.total == 2

    only_admins = AuthService(session).list_users(role=Role.ADMIN)
    assert only_admins.total == 1
    assert only_admins.items[0].role == Role.ADMIN


# ── update_user ───────────────────────────────────────────
def test_update_user_changes_role_and_status(session):
    admin, _ = AuthService(session).create_staff(role=Role.ADMIN, **STAFF)
    target = AuthService(session).register(**VALID)

    updated = AuthService(session).update_user(
        actor=admin, target_id=target.id, role=Role.DELIVERY, status=UserStatus.SUSPENDED
    )

    assert updated.role == Role.DELIVERY
    assert updated.status == UserStatus.SUSPENDED


def test_update_user_only_role_leaves_status_untouched(session):
    admin, _ = AuthService(session).create_staff(role=Role.ADMIN, **STAFF)
    target = AuthService(session).register(**VALID)

    updated = AuthService(session).update_user(actor=admin, target_id=target.id, role=Role.ADMIN)

    assert updated.role == Role.ADMIN
    assert updated.status == UserStatus.ACTIVE  # sin tocar


def test_update_user_writes_an_audit_entry(session):
    admin, _ = AuthService(session).create_staff(role=Role.ADMIN, **STAFF)
    target = AuthService(session).register(**VALID)

    AuthService(session).update_user(
        actor=admin, target_id=target.id, status=UserStatus.SUSPENDED, ip="10.0.0.1"
    )

    entry = session.scalars(select(AuditLog)).one()
    assert entry.actor_id == admin.id
    assert entry.action == "user.update_role_status"
    assert entry.entity_type == "user"
    assert entry.entity_id == str(target.id)
    assert entry.ip == "10.0.0.1"
    assert '"before"' in entry.data and '"after"' in entry.data


def test_update_user_nonexistent_target_raises_not_found(session):
    admin, _ = AuthService(session).create_staff(role=Role.ADMIN, **STAFF)
    with pytest.raises(NotFoundError):
        AuthService(session).update_user(actor=admin, target_id=999_999, role=Role.ADMIN)


def test_update_user_without_role_or_status_raises_invalid_input(session):
    admin, _ = AuthService(session).create_staff(role=Role.ADMIN, **STAFF)
    target = AuthService(session).register(**VALID)
    with pytest.raises(InvalidInputError):
        AuthService(session).update_user(actor=admin, target_id=target.id)


def test_suspended_user_cannot_login(session):
    admin, _ = AuthService(session).create_staff(role=Role.ADMIN, **STAFF)
    AuthService(session).register(**VALID)

    AuthService(session).update_user(
        actor=admin,
        target_id=UserRepository(session).get_by_email(VALID["email"]).id,
        status=UserStatus.SUSPENDED,
    )

    with pytest.raises(ForbiddenError):
        AuthService(session).authenticate(VALID["email"], VALID["password"])


# ── login_with_google ────────────────────────────────────
GOOGLE = {
    "sub": "1234567890",
    "email": "gustavo@morficenter.test",
    "first_name": "Gustavo",
    "last_name": "Pérez",
}


def test_login_with_google_creates_a_new_customer_without_password(session):
    user = AuthService(session).login_with_google(**GOOGLE)

    assert user.id is not None
    assert user.role == Role.CUSTOMER
    assert user.status == UserStatus.ACTIVE
    assert user.password_hash is None
    assert user.email == GOOGLE["email"]


def test_login_with_google_new_user_links_google_provider_and_creates_cart_and_balance(session):
    user = AuthService(session).login_with_google(**GOOGLE)
    session.refresh(user)

    assert len(user.auth_providers) == 1
    assert user.auth_providers[0].provider == AuthProvider.GOOGLE
    assert user.auth_providers[0].provider_uid == GOOGLE["sub"]
    assert user.cart is not None
    assert user.balance is not None
    assert user.balance.balance == 0


def test_login_with_google_second_call_with_same_sub_is_a_login(session):
    first = AuthService(session).login_with_google(**GOOGLE)
    second = AuthService(session).login_with_google(**GOOGLE)

    assert second.id == first.id
    session.refresh(second)
    assert len(second.auth_providers) == 1  # no duplica el provider


def test_login_with_google_links_to_an_existing_local_account_by_email(session):
    local_user = AuthService(session).register(**VALID)  # email = gustavo@morficenter.test

    linked = AuthService(session).login_with_google(**GOOGLE)

    assert linked.id == local_user.id
    session.refresh(linked)
    providers = {p.provider for p in linked.auth_providers}
    assert providers == {AuthProvider.LOCAL, AuthProvider.GOOGLE}
    # la contraseña local no se toca: sigue pudiendo loguearse con ella.
    assert verify_password(VALID["password"], linked.password_hash) is True


def test_login_with_google_does_not_duplicate_cart_or_balance_when_linking(session):
    local_user = AuthService(session).register(**VALID)
    session.refresh(local_user)
    original_cart_id = local_user.cart.id

    linked = AuthService(session).login_with_google(**GOOGLE)
    session.refresh(linked)

    assert linked.cart.id == original_cart_id  # no crea uno nuevo


def test_login_with_google_suspended_account_raises_forbidden(session):
    admin, _ = AuthService(session).create_staff(role=Role.ADMIN, **STAFF)
    local_user = AuthService(session).register(**VALID)
    AuthService(session).update_user(
        actor=admin, target_id=local_user.id, status=UserStatus.SUSPENDED
    )

    with pytest.raises(ForbiddenError):
        AuthService(session).login_with_google(**GOOGLE)


# ── request_password_reset / reset_password ──────────────
def test_request_password_reset_returns_a_token_for_a_local_active_account(session):
    AuthService(session).register(**VALID)
    token = AuthService(session).request_password_reset(VALID["email"])
    assert token is not None


def test_request_password_reset_unknown_email_returns_none(session):
    assert AuthService(session).request_password_reset("nadie@morficenter.test") is None


def test_request_password_reset_suspended_account_returns_none(session):
    admin, _ = AuthService(session).create_staff(role=Role.ADMIN, **STAFF)
    target = AuthService(session).register(**VALID)
    AuthService(session).update_user(actor=admin, target_id=target.id, status=UserStatus.SUSPENDED)

    assert AuthService(session).request_password_reset(VALID["email"]) is None


def test_request_password_reset_google_only_account_returns_none(session):
    AuthService(session).login_with_google(**GOOGLE)  # password_hash=None
    assert AuthService(session).request_password_reset(GOOGLE["email"]) is None


def test_reset_password_changes_the_password(session):
    user = AuthService(session).register(**VALID)
    token = AuthService(session).request_password_reset(VALID["email"])

    AuthService(session).reset_password(token, "nuevaClave123")

    session.refresh(user)
    assert verify_password("nuevaClave123", user.password_hash) is True
    assert verify_password(VALID["password"], user.password_hash) is False


def test_reset_password_token_is_single_use(session):
    AuthService(session).register(**VALID)
    token = AuthService(session).request_password_reset(VALID["email"])

    AuthService(session).reset_password(token, "nuevaClave123")
    with pytest.raises(InvalidInputError) as exc:
        AuthService(session).reset_password(token, "otraClave456")
    assert exc.value.details["field"] == "token"


def test_reset_password_expired_token_raises_invalid_input(session):
    user = AuthService(session).register(**VALID)
    stale = now_utc() - timedelta(minutes=settings.password_reset_token_minutes + 1)
    token, _jti = create_password_reset_token(user.id, now=stale)

    with pytest.raises(InvalidInputError) as exc:
        AuthService(session).reset_password(token, "nuevaClave123")
    assert exc.value.details["field"] == "token"


def test_reset_password_malformed_token_raises_invalid_input(session):
    with pytest.raises(InvalidInputError):
        AuthService(session).reset_password("no-soy-un-jwt", "nuevaClave123")


def test_reset_password_empty_token_raises_invalid_input(session):
    with pytest.raises(InvalidInputError):
        AuthService(session).reset_password("", "nuevaClave123")


def test_reset_password_wrong_token_type_raises_invalid_input(session):
    user = AuthService(session).register(**VALID)
    access_token = create_access_token(user.id, user.role)
    with pytest.raises(InvalidInputError):
        AuthService(session).reset_password(access_token, "nuevaClave123")


def test_reset_password_weak_new_password_raises_invalid_input(session):
    AuthService(session).register(**VALID)
    token = AuthService(session).request_password_reset(VALID["email"])
    with pytest.raises(InvalidInputError) as exc:
        AuthService(session).reset_password(token, "short")
    assert exc.value.details["field"] == "password"


def test_reset_password_for_suspended_account_raises_invalid_input(session):
    admin, _ = AuthService(session).create_staff(role=Role.ADMIN, **STAFF)
    target = AuthService(session).register(**VALID)
    token = AuthService(session).request_password_reset(VALID["email"])

    AuthService(session).update_user(actor=admin, target_id=target.id, status=UserStatus.SUSPENDED)

    with pytest.raises(InvalidInputError):
        AuthService(session).reset_password(token, "nuevaClave123")
