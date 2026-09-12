"""`SettingsService` (`03_Roadmap.md` T-2.1.2, T-2.1.3)."""

import pytest
from sqlalchemy import select

from app.core.enums import CoverageMode, Role, ShippingMode, UserStatus
from app.core.errors import InvalidInputError
from app.models.audit import AuditLog
from app.models.settings import SystemSetting
from app.models.user import User
from app.services.settings_service import (
    SETTINGS_DEFAULTS,
    GeoPoint,
    PaymentTransfer,
    SettingKey,
    SettingsService,
    ShiftDefault,
    ShippingTier,
)


def _service(session) -> SettingsService:
    return SettingsService(session)


# ── getters: devuelven el default de §6.11 cuando la clave no existe ──
def test_get_shift_default_without_a_stored_value_returns_the_default(session):
    result = _service(session).get_shift_default()
    assert result == ShiftDefault.model_validate(SETTINGS_DEFAULTS[SettingKey.SHIFT_DEFAULT])


def test_get_timezone_without_a_stored_value_returns_the_default(session):
    assert _service(session).get_timezone() == "America/Argentina/Buenos_Aires"


def test_get_coverage_mode_without_a_stored_value_returns_the_default(session):
    assert _service(session).get_coverage_mode() == CoverageMode.NEIGHBORHOOD_AND_RADIUS


def test_get_coverage_origin_without_a_stored_value_returns_the_default(session):
    origin = _service(session).get_coverage_origin()
    assert origin == GeoPoint(lat=-34.63, lng=-58.41)


def test_get_shipping_mode_without_a_stored_value_returns_the_default(session):
    assert _service(session).get_shipping_mode() == ShippingMode.BY_DISTANCE


def test_get_shipping_flat_amount_without_a_stored_value_returns_the_default(session):
    assert _service(session).get_shipping_flat_amount() == 200000


def test_get_shipping_tiers_without_a_stored_value_returns_the_default(session):
    tiers = _service(session).get_shipping_tiers()
    assert tiers == [
        ShippingTier(max_km=2, amount=100000),
        ShippingTier(max_km=4, amount=150000),
        ShippingTier(max_km=6, amount=250000),
    ]


def test_get_payment_transfer_without_a_stored_value_returns_the_default(session):
    transfer = _service(session).get_payment_transfer()
    assert transfer.alias == "MORFI.CENTER"


def test_get_stock_reservation_ttl_min_without_a_stored_value_returns_the_default(session):
    assert _service(session).get_stock_reservation_ttl_min() == 40


def test_get_promo_tie_breaker_without_a_stored_value_returns_the_default(session):
    assert _service(session).get_promo_tie_breaker() == "lowest_price"


def test_get_orders_code_prefix_without_a_stored_value_returns_the_default(session):
    assert _service(session).get_orders_code_prefix() == "MC"


# ── set: guarda un valor válido y el getter lo refleja ─────
def test_set_shift_default_with_a_valid_value_persists(session):
    svc = _service(session)
    new_shift = {
        "open": "09:00",
        "close": "13:00",
        "prep_eta": "13:15",
        "dispatch_eta": "13:30",
        "cancel_window_min": 15,
        "weekdays": [1, 2, 3, 4, 5, 6],
    }
    svc.set(SettingKey.SHIFT_DEFAULT, new_shift)
    assert svc.get_shift_default() == ShiftDefault.model_validate(new_shift)


def test_set_coverage_mode_with_a_valid_value_persists(session):
    svc = _service(session)
    svc.set(SettingKey.COVERAGE_MODE, "radius")
    assert svc.get_coverage_mode() == CoverageMode.RADIUS


def test_set_shipping_tiers_with_a_valid_value_persists(session):
    svc = _service(session)
    svc.set(SettingKey.SHIPPING_TIERS, [{"max_km": 5, "amount": 300000}])
    assert svc.get_shipping_tiers() == [ShippingTier(max_km=5, amount=300000)]


def test_set_payment_transfer_with_a_valid_value_persists(session):
    svc = _service(session)
    payload = {"alias": "OTRO.ALIAS", "holder": "Juan", "bank": "Banco X", "cbu": "123"}
    svc.set(SettingKey.PAYMENT_TRANSFER, payload)
    assert svc.get_payment_transfer() == PaymentTransfer.model_validate(payload)


# ── set: forma inválida -> InvalidInputError ───────────────
def test_set_shift_default_missing_a_field_raises(session):
    with pytest.raises(InvalidInputError) as exc:
        _service(session).set(SettingKey.SHIFT_DEFAULT, {"open": "08:00"})
    assert exc.value.details["field"] == "shift.default"


def test_set_coverage_mode_invalid_enum_value_raises(session):
    with pytest.raises(InvalidInputError) as exc:
        _service(session).set(SettingKey.COVERAGE_MODE, "not-a-real-mode")
    assert exc.value.details["field"] == "coverage.mode"


def test_set_shipping_mode_invalid_enum_value_raises(session):
    with pytest.raises(InvalidInputError):
        _service(session).set(SettingKey.SHIPPING_MODE, "teleport")


def test_set_coverage_origin_missing_lng_raises(session):
    with pytest.raises(InvalidInputError):
        _service(session).set(SettingKey.COVERAGE_ORIGIN, {"lat": -34.63})


def test_set_shipping_tiers_not_a_list_raises(session):
    with pytest.raises(InvalidInputError):
        _service(session).set(SettingKey.SHIPPING_TIERS, {"max_km": 2, "amount": 100000})


def test_set_shipping_tiers_empty_list_raises(session):
    with pytest.raises(InvalidInputError):
        _service(session).set(SettingKey.SHIPPING_TIERS, [])


def test_set_payment_transfer_missing_a_field_raises(session):
    with pytest.raises(InvalidInputError):
        _service(session).set(SettingKey.PAYMENT_TRANSFER, {"alias": "X"})


def test_set_shipping_flat_amount_negative_raises(session):
    with pytest.raises(InvalidInputError):
        _service(session).set(SettingKey.SHIPPING_FLAT_AMOUNT, -1)


def test_set_shipping_flat_amount_non_int_raises(session):
    with pytest.raises(InvalidInputError):
        _service(session).set(SettingKey.SHIPPING_FLAT_AMOUNT, "200000")


def test_set_stock_reservation_ttl_min_negative_raises(session):
    with pytest.raises(InvalidInputError):
        _service(session).set(SettingKey.STOCK_RESERVATION_TTL_MIN, -5)


def test_set_promo_tie_breaker_invalid_value_raises(session):
    with pytest.raises(InvalidInputError):
        _service(session).set(SettingKey.PROMO_TIE_BREAKER, "coin_flip")


def test_set_timezone_empty_string_raises(session):
    with pytest.raises(InvalidInputError):
        _service(session).set(SettingKey.TIMEZONE, "   ")


def test_set_orders_code_prefix_empty_string_raises(session):
    with pytest.raises(InvalidInputError):
        _service(session).set(SettingKey.ORDERS_CODE_PREFIX, "")


# ── set: registra el actor en el repo subyacente ───────────
def test_set_passes_the_actor_through_to_the_repository(session):
    admin = User(
        first_name="Root",
        last_name="Admin",
        email="admin@morficenter.test",
        role=Role.ADMIN,
        status=UserStatus.ACTIVE,
    )
    session.add(admin)
    session.flush()

    _service(session).set(SettingKey.ORDERS_CODE_PREFIX, "MC2", actor_id=admin.id)

    stored = session.get(SystemSetting, SettingKey.ORDERS_CODE_PREFIX.value)
    assert stored.updated_by == admin.id


# ── get_all ─────────────────────────────────────────────────
def test_get_all_returns_every_known_key_with_its_effective_value(session):
    result = _service(session).get_all()
    assert set(result.keys()) == {key.value for key in SettingKey}
    assert result[SettingKey.TIMEZONE.value] == "America/Argentina/Buenos_Aires"


def test_get_all_reflects_a_saved_override(session):
    svc = _service(session)
    svc.set(SettingKey.ORDERS_CODE_PREFIX, "XX")
    assert svc.get_all()[SettingKey.ORDERS_CODE_PREFIX.value] == "XX"


# ── set: audita el cambio (T-2.1.3) ─────────────────────────
def test_set_writes_an_audit_entry_with_before_and_after(session):
    admin = User(
        first_name="Root",
        last_name="Admin",
        email="admin2@morficenter.test",
        role=Role.ADMIN,
        status=UserStatus.ACTIVE,
    )
    session.add(admin)
    session.flush()

    _service(session).set(SettingKey.ORDERS_CODE_PREFIX, "XX", actor_id=admin.id)

    entry = session.scalars(select(AuditLog)).one()
    assert entry.actor_id == admin.id
    assert entry.action == "settings.update"
    assert entry.entity_type == "system_setting"
    assert entry.entity_id == "orders.code_prefix"
    assert '"before": "MC"' in entry.data
    assert '"after": "XX"' in entry.data


def test_set_does_not_write_an_audit_entry_when_validation_fails(session):
    with pytest.raises(InvalidInputError):
        _service(session).set(SettingKey.ORDERS_CODE_PREFIX, "")
    assert session.scalars(select(AuditLog)).first() is None
