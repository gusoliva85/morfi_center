"""Claves conocidas de `system_settings`, sus defaults y su validación de
forma (`03_Roadmap.md` T-2.1.2). Ver `documentacion/02_Documento_Tecnico.md §6.11`.

`SettingsService` es la única puerta de escritura de estas claves: valida la
forma de cada una antes de guardarla (`InvalidInputError` si no cumple),
audita el cambio (T-2.1.3) y expone un getter tipado por clave
(`get_shift_default()`, etc.) que aplica el default de §6.11 cuando la
clave todavía no existe en la base.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.core.enums import CoverageMode, ShippingMode
from app.core.errors import InvalidInputError
from app.repositories.audit_repository import AuditLogRepository
from app.repositories.settings_repository import SettingsRepository


class SettingKey(StrEnum):
    """Las claves que la aplicación conoce y sabe validar/tipar."""

    SHIFT_DEFAULT = "shift.default"
    TIMEZONE = "timezone"
    COVERAGE_MODE = "coverage.mode"
    COVERAGE_ORIGIN = "coverage.origin"
    SHIPPING_MODE = "shipping.mode"
    SHIPPING_FLAT_AMOUNT = "shipping.flat_amount"
    SHIPPING_TIERS = "shipping.tiers"
    PAYMENT_TRANSFER = "payment.transfer"
    STOCK_RESERVATION_TTL_MIN = "stock.reservation_ttl_min"
    PROMO_TIE_BREAKER = "promo.tie_breaker"
    ORDERS_CODE_PREFIX = "orders.code_prefix"


# ══════════════════════════════════════════════════════════
#  Formas (Pydantic) de las claves estructuradas
# ══════════════════════════════════════════════════════════


class ShiftDefault(BaseModel):
    open: str
    close: str
    prep_eta: str
    dispatch_eta: str
    cancel_window_min: int
    weekdays: list[int]


class GeoPoint(BaseModel):
    lat: float
    lng: float


class ShippingTier(BaseModel):
    max_km: float
    amount: int


class PaymentTransfer(BaseModel):
    alias: str
    holder: str
    bank: str
    cbu: str


PROMO_TIE_BREAKERS = ("lowest_price", "priority")

# ══════════════════════════════════════════════════════════
#  Defaults (documentacion/02_Documento_Tecnico.md §6.11)
# ══════════════════════════════════════════════════════════

SETTINGS_DEFAULTS: dict[SettingKey, Any] = {
    SettingKey.SHIFT_DEFAULT: {
        "open": "08:00",
        "close": "12:00",
        "prep_eta": "12:15",
        "dispatch_eta": "12:30",
        "cancel_window_min": 20,
        "weekdays": [1, 2, 3, 4, 5],
    },
    SettingKey.TIMEZONE: "America/Argentina/Buenos_Aires",
    SettingKey.COVERAGE_MODE: CoverageMode.NEIGHBORHOOD_AND_RADIUS.value,
    SettingKey.COVERAGE_ORIGIN: {"lat": -34.63, "lng": -58.41},
    SettingKey.SHIPPING_MODE: ShippingMode.BY_DISTANCE.value,
    SettingKey.SHIPPING_FLAT_AMOUNT: 200000,
    SettingKey.SHIPPING_TIERS: [
        {"max_km": 2, "amount": 100000},
        {"max_km": 4, "amount": 150000},
        {"max_km": 6, "amount": 250000},
    ],
    SettingKey.PAYMENT_TRANSFER: {
        "alias": "MORFI.CENTER",
        "holder": "",
        "bank": "",
        "cbu": "",
    },
    SettingKey.STOCK_RESERVATION_TTL_MIN: 40,
    SettingKey.PROMO_TIE_BREAKER: "lowest_price",
    SettingKey.ORDERS_CODE_PREFIX: "MC",
}


# ══════════════════════════════════════════════════════════
#  Validadores de forma por clave
# ══════════════════════════════════════════════════════════


def _validate_model(model: type[BaseModel], value: Any) -> dict[str, Any]:
    try:
        return model.model_validate(value).model_dump()
    except ValidationError as exc:
        raise InvalidInputError(
            "El valor no tiene la forma esperada.",
            details={"errors": exc.errors(include_url=False, include_context=False)},
        ) from exc


def _validate_enum(enum_cls: type[StrEnum], value: Any) -> str:
    try:
        return enum_cls(value).value
    except ValueError as exc:
        valid_values = [member.value for member in enum_cls]
        raise InvalidInputError(f"Valor inválido: tiene que ser uno de {valid_values}.") from exc


def _validate_non_negative_int(value: Any) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise InvalidInputError("Tiene que ser un número entero, mayor o igual a 0.")
    return value


def _validate_non_empty_string(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidInputError("Tiene que ser un texto no vacío.")
    return value


def _validate_shipping_tiers(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise InvalidInputError("Tiene que ser una lista con al menos un tramo.")
    return [_validate_model(ShippingTier, item) for item in value]


def _validate_promo_tie_breaker(value: Any) -> str:
    if value not in PROMO_TIE_BREAKERS:
        raise InvalidInputError(f"Tiene que ser uno de {PROMO_TIE_BREAKERS}.")
    return value


_VALIDATORS: dict[SettingKey, Any] = {
    SettingKey.SHIFT_DEFAULT: lambda v: _validate_model(ShiftDefault, v),
    SettingKey.TIMEZONE: _validate_non_empty_string,
    SettingKey.COVERAGE_MODE: lambda v: _validate_enum(CoverageMode, v),
    SettingKey.COVERAGE_ORIGIN: lambda v: _validate_model(GeoPoint, v),
    SettingKey.SHIPPING_MODE: lambda v: _validate_enum(ShippingMode, v),
    SettingKey.SHIPPING_FLAT_AMOUNT: _validate_non_negative_int,
    SettingKey.SHIPPING_TIERS: _validate_shipping_tiers,
    SettingKey.PAYMENT_TRANSFER: lambda v: _validate_model(PaymentTransfer, v),
    SettingKey.STOCK_RESERVATION_TTL_MIN: _validate_non_negative_int,
    SettingKey.PROMO_TIE_BREAKER: _validate_promo_tie_breaker,
    SettingKey.ORDERS_CODE_PREFIX: _validate_non_empty_string,
}


class SettingsService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.settings = SettingsRepository(session)
        self.audit = AuditLogRepository(session)

    def _get(self, key: SettingKey) -> Any:
        return self.settings.get(key.value, default=SETTINGS_DEFAULTS[key])

    def get_all(self) -> dict[str, Any]:
        """El valor efectivo (guardado, o el default) de cada clave conocida."""
        return {key.value: self._get(key) for key in SettingKey}

    def set(self, key: SettingKey, value: Any, *, actor_id: int | None = None) -> Any:
        """Valida la forma de `value` según `key`, la guarda y audita el
        cambio (`audit_log`, before/after). Devuelve el valor ya
        validado/normalizado.

        :raises InvalidInputError: si `value` no tiene la forma esperada
            para esa clave.
        """
        try:
            validated = _VALIDATORS[key](value)
        except InvalidInputError as exc:
            exc.details.setdefault("field", key.value)
            raise

        before = self._get(key)
        self.settings.set(key.value, validated, actor_id=actor_id)
        self.audit.record(
            actor_id=actor_id,
            action="settings.update",
            entity_type="system_setting",
            entity_id=key.value,
            data={"before": before, "after": validated},
        )
        return validated

    def get_shift_default(self) -> ShiftDefault:
        return ShiftDefault.model_validate(self._get(SettingKey.SHIFT_DEFAULT))

    def get_timezone(self) -> str:
        return self._get(SettingKey.TIMEZONE)

    def get_coverage_mode(self) -> CoverageMode:
        return CoverageMode(self._get(SettingKey.COVERAGE_MODE))

    def get_coverage_origin(self) -> GeoPoint:
        return GeoPoint.model_validate(self._get(SettingKey.COVERAGE_ORIGIN))

    def get_shipping_mode(self) -> ShippingMode:
        return ShippingMode(self._get(SettingKey.SHIPPING_MODE))

    def get_shipping_flat_amount(self) -> int:
        return self._get(SettingKey.SHIPPING_FLAT_AMOUNT)

    def get_shipping_tiers(self) -> list[ShippingTier]:
        return [ShippingTier.model_validate(item) for item in self._get(SettingKey.SHIPPING_TIERS)]

    def get_payment_transfer(self) -> PaymentTransfer:
        return PaymentTransfer.model_validate(self._get(SettingKey.PAYMENT_TRANSFER))

    def get_stock_reservation_ttl_min(self) -> int:
        return self._get(SettingKey.STOCK_RESERVATION_TTL_MIN)

    def get_promo_tie_breaker(self) -> str:
        return self._get(SettingKey.PROMO_TIE_BREAKER)

    def get_orders_code_prefix(self) -> str:
        return self._get(SettingKey.ORDERS_CODE_PREFIX)


__all__ = [
    "SettingKey",
    "SETTINGS_DEFAULTS",
    "ShiftDefault",
    "GeoPoint",
    "ShippingTier",
    "PaymentTransfer",
    "PROMO_TIE_BREAKERS",
    "SettingsService",
]
