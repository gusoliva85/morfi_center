import pytest
from sqlalchemy import text

from app.core.enums import CoverageMode, PromoTieBreaker, SettingKey, ShippingMode
from app.core.errors import DomainValidationError, NotFoundError, SettingCorruptError
from app.services.settings_service import SPECS, SettingsService

VALID_SHIFT = {
    "open": "08:00",
    "close": "12:00",
    "prep_eta": "12:15",
    "dispatch_eta": "12:30",
    "cancel_window_min": 20,
    "weekdays": [1, 2, 3, 4, 5],
}


@pytest.fixture()
def service(session) -> SettingsService:
    return SettingsService(session)


def fields_of(exc_info) -> dict[str, str]:
    return {f["field"]: f["message"] for f in exc_info.value.details["fields"]}


# ---------- catálogo ----------


def test_every_known_key_has_a_spec():
    assert set(SPECS) == set(SettingKey)


@pytest.mark.parametrize("key", list(SettingKey))
def test_every_default_passes_its_own_validation(key):
    """Si un default no cumpliera su propia forma, el sistema arrancaría roto."""
    spec = SPECS[key]
    spec.adapter.validate_python(spec.default)


@pytest.mark.parametrize("key", list(SettingKey))
def test_every_key_has_a_description(key):
    assert SPECS[key].description


# ---------- lectura: defaults ----------


def test_reading_an_unset_key_returns_its_default(service):
    shift = service.get_shift_default()

    assert (shift.open, shift.close) == ("08:00", "12:00")
    assert shift.cancel_window_min == 20
    assert shift.weekdays == [1, 2, 3, 4, 5]


def test_typed_getters_return_typed_defaults(service):
    assert service.get_timezone() == "America/Argentina/Buenos_Aires"
    assert service.get_coverage_mode() is CoverageMode.NEIGHBORHOOD_AND_RADIUS
    assert service.get_shipping_mode() is ShippingMode.BY_DISTANCE
    assert service.get_shipping_flat_amount() == 200000
    assert service.get_stock_reservation_ttl_min() == 40
    assert service.get_promo_tie_breaker() is PromoTieBreaker.LOWEST_PRICE
    assert service.get_order_code_prefix() == "MC"
    assert service.get_coverage_origin().lat == -34.63
    assert [t.max_km for t in service.get_shipping_tiers()] == [2, 4, 6]


def test_default_payment_transfer_has_no_made_up_bank_data(service):
    transfer = service.get_payment_transfer()

    assert transfer.alias == "MORFI.CENTER"
    assert (transfer.holder, transfer.bank, transfer.cbu) == ("", "", "")


def test_reading_does_not_write_the_default_to_the_database(service):
    service.get_shift_default()

    assert service.repo.list_all() == []


# ---------- escritura válida ----------


def test_a_saved_value_is_read_back_instead_of_the_default(service):
    service.set("stock.reservation_ttl_min", 25)

    assert service.get_stock_reservation_ttl_min() == 25


def test_a_saved_object_is_read_back_as_a_typed_model(service):
    service.set("shift.default", {**VALID_SHIFT, "close": "13:30"})

    assert service.get_shift_default().close == "13:30"


def test_an_enum_value_is_stored_as_its_plain_string(service):
    service.set("coverage.mode", "radius")

    assert service.repo.get("coverage.mode") == "radius"
    assert service.get_coverage_mode() is CoverageMode.RADIUS


def test_the_stored_form_is_canonical(service):
    """Lo que queda guardado es lo validado, no lo que llegó: sin espacios de
    más y con los días ordenados."""
    service.set("payment.transfer", {"alias": "  MI.ALIAS  ", "holder": "", "bank": "", "cbu": ""})
    service.set("shift.default", {**VALID_SHIFT, "weekdays": [5, 1, 3]})

    assert service.repo.get("payment.transfer")["alias"] == "MI.ALIAS"
    assert service.repo.get("shift.default")["weekdays"] == [1, 3, 5]


def test_set_records_the_actor(service, session):
    from app.core.enums import Role
    from app.repositories.user_repository import UserRepository

    admin = UserRepository(session).create(
        first_name="A", last_name="B", email="a@example.com", password_hash="x", role=Role.ADMIN
    )
    session.flush()

    row = service.set("orders.code_prefix", "PED", actor=admin)

    assert row.updated_by == admin.id


def test_set_accepts_a_valid_cbu(service):
    service.set(
        "payment.transfer",
        {"alias": "MORFI.CENTER", "holder": "Ana", "bank": "Banco", "cbu": "0" * 22},
    )

    assert service.get_payment_transfer().cbu == "0" * 22


def test_set_accepts_km_and_coordinates_as_int_or_float(service):
    service.set("coverage.origin", {"lat": -34, "lng": -58.5})
    service.set("shipping.tiers", [{"max_km": 1.5, "amount": 0}, {"max_km": 3, "amount": 5}])

    assert service.get_coverage_origin().lat == -34
    assert [t.max_km for t in service.get_shipping_tiers()] == [1.5, 3]


# ---------- escritura inválida ----------


def test_an_unknown_key_is_rejected(service):
    with pytest.raises(NotFoundError):
        service.set("shipping.tier", 1)


def test_nothing_is_saved_when_the_value_is_invalid(service):
    with pytest.raises(DomainValidationError):
        service.set("stock.reservation_ttl_min", 0)

    assert service.repo.list_all() == []


def test_the_error_uses_the_project_validation_format(service):
    with pytest.raises(DomainValidationError) as exc_info:
        service.set("stock.reservation_ttl_min", 0)

    assert exc_info.value.status_code == 422
    assert exc_info.value.code == "VALIDATION_ERROR"
    assert fields_of(exc_info) == {"value": "Tiene que ser mayor o igual a 1."}


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("stock.reservation_ttl_min", "40"),  # texto en vez de número
        ("stock.reservation_ttl_min", True),  # un booleano no es un número
        ("stock.reservation_ttl_min", 4.5),
        ("shipping.flat_amount", -1),
        ("shipping.flat_amount", "200000"),
        ("timezone", "Marte/Olympus_Mons"),
        ("timezone", ""),
        ("timezone", 3),
        ("coverage.mode", "en_cualquier_lado"),
        ("shipping.mode", "gratis"),
        ("promo.tie_breaker", "random"),
        ("orders.code_prefix", "mc"),  # tiene que ir en mayúscula
        ("orders.code_prefix", ""),
        ("orders.code_prefix", "DEMASIADO"),
        ("coverage.origin", {"lat": 91, "lng": 0}),
        ("coverage.origin", {"lat": 0, "lng": -181}),
        ("coverage.origin", {"lat": 0}),  # falta lng
        ("coverage.origin", {"lat": True, "lng": 0}),
        ("coverage.origin", {"lat": 0, "lng": 0, "alt": 1}),  # campo de más
        ("coverage.origin", "-34.63,-58.41"),
    ],
)
def test_invalid_values_are_rejected(service, key, value):
    with pytest.raises(DomainValidationError):
        service.set(key, value)


@pytest.mark.parametrize(
    ("change", "field"),
    [
        ({"open": "8:00"}, "open"),
        ({"open": "24:00"}, "open"),
        ({"close": "12:60"}, "close"),
        ({"close": "mediodía"}, "close"),
        ({"prep_eta": "tarde"}, "prep_eta"),
        ({"cancel_window_min": -5}, "cancel_window_min"),
        ({"cancel_window_min": "20"}, "cancel_window_min"),
        ({"weekdays": []}, "weekdays"),
        ({"weekdays": [0, 1]}, "weekdays.0"),
        ({"weekdays": [1, 8]}, "weekdays.1"),
        ({"weekdays": [1, 1, 2]}, "weekdays"),
        ({"turno_doble": True}, "turno_doble"),
    ],
)
def test_invalid_shift_fields_point_at_the_offending_field(service, change, field):
    with pytest.raises(DomainValidationError) as exc_info:
        service.set("shift.default", {**VALID_SHIFT, **change})

    assert field in fields_of(exc_info)


def test_a_missing_shift_field_is_reported(service):
    incomplete = {k: v for k, v in VALID_SHIFT.items() if k != "close"}

    with pytest.raises(DomainValidationError) as exc_info:
        service.set("shift.default", incomplete)

    assert fields_of(exc_info) == {"close": "Es obligatorio."}


def test_the_shift_must_close_after_it_opens(service):
    with pytest.raises(DomainValidationError) as exc_info:
        service.set("shift.default", {**VALID_SHIFT, "open": "12:00", "close": "08:00"})

    assert "posterior" in fields_of(exc_info)["value"]


def test_the_cancel_window_cannot_be_longer_than_the_shift(service):
    with pytest.raises(DomainValidationError):
        service.set("shift.default", {**VALID_SHIFT, "cancel_window_min": 241})  # turno de 240 min


def test_the_etas_are_optional(service):
    without_etas = {k: v for k, v in VALID_SHIFT.items() if k not in ("prep_eta", "dispatch_eta")}

    service.set("shift.default", without_etas)

    assert service.get_shift_default().prep_eta is None


@pytest.mark.parametrize(
    "tiers",
    [
        [],  # sin ningún rango no se puede cotizar
        [{"max_km": 4, "amount": 1}, {"max_km": 2, "amount": 2}],  # desordenados
        [{"max_km": 2, "amount": 1}, {"max_km": 2, "amount": 2}],  # repetido
        [{"max_km": 2, "amount": -1}],
        [{"max_km": 0, "amount": 1}],
        [{"max_km": 2}],
        [{"max_km": 2, "amount": 1, "extra": 1}],
    ],
)
def test_invalid_shipping_tiers_are_rejected(service, tiers):
    with pytest.raises(DomainValidationError):
        service.set("shipping.tiers", tiers)


@pytest.mark.parametrize(
    "change",
    [
        {"alias": ""},
        {"alias": "   "},
        {"cbu": "123"},
        {"cbu": "1" * 21 + "x"},
        {"holder": 5},
    ],
)
def test_invalid_payment_transfer_is_rejected(service, change):
    base = {"alias": "MORFI.CENTER", "holder": "", "bank": "", "cbu": ""}

    with pytest.raises(DomainValidationError):
        service.set("payment.transfer", {**base, **change})


def test_an_enum_error_lists_the_allowed_options(service):
    with pytest.raises(DomainValidationError) as exc_info:
        service.set("shipping.mode", "gratis")

    message = fields_of(exc_info)["value"]
    assert "free" in message and "by_distance" in message
    assert " or " not in message  # el conector también va en español


def test_a_bad_code_prefix_says_what_is_expected(service):
    with pytest.raises(DomainValidationError) as exc_info:
        service.set("orders.code_prefix", "mc")

    assert "mayúsculas" in fields_of(exc_info)["value"]


# ---------- lectura de datos corruptos ----------


def test_a_corrupt_stored_value_fails_loudly(service, session):
    """Alguien editó la base a mano: mejor un error claro que asumir un horario."""
    session.execute(
        text(
            "INSERT INTO system_settings (key, value, value_type, updated_at) "
            "VALUES ('shift.default', '{\"open\": \"cualquier cosa\"}', 'json', CURRENT_TIMESTAMP)"
        )
    )

    with pytest.raises(SettingCorruptError) as exc_info:
        service.get_shift_default()

    assert exc_info.value.details == {"key": "shift.default"}


def test_a_stored_value_that_is_not_json_fails_loudly(service, session):
    session.execute(
        text(
            "INSERT INTO system_settings (key, value, value_type, updated_at) "
            "VALUES ('timezone', 'no es json', 'string', CURRENT_TIMESTAMP)"
        )
    )

    with pytest.raises(SettingCorruptError):
        service.get_timezone()
