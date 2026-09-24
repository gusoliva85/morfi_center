import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic import TypeAdapter, ValidationError
from sqlalchemy.orm import Session

from app.core.enums import (
    CoverageMode,
    PromoTieBreaker,
    SettingKey,
    SettingValueType,
    ShippingMode,
)
from app.core.errors import DomainValidationError, NotFoundError, SettingCorruptError
from app.models import AuditLog, User
from app.repositories.settings_repository import SettingsRepository, infer_value_type
from app.schemas.settings import (
    CoverageOrigin,
    Money,
    OrderCodePrefix,
    PaymentTransfer,
    ReservationTtlMin,
    ShiftDefault,
    ShippingTier,
    ShippingTiers,
    Timezone,
)

UNKNOWN_KEY = "No existe esa configuración."
INVALID_VALUE = "El valor no es válido para esta configuración."


@dataclass(frozen=True)
class SettingSpec:
    """Todo lo que el sistema sabe de una clave: cómo validarla, con qué valor
    arranca y para qué sirve (el texto que muestra el panel de admin)."""

    key: SettingKey
    adapter: TypeAdapter
    default: Any  # valor JSON (lo que se guarda), no el objeto ya validado
    description: str


@dataclass(frozen=True)
class SettingView:
    """Una configuración tal como la ve la API: el valor vigente (guardado o
    default) más de dónde viene."""

    key: str
    value: Any
    value_type: SettingValueType
    description: str
    is_default: bool  # True: nadie la guardó todavía, rige el valor por defecto
    updated_at: datetime | None
    updated_by: int | None


def _spec(key: SettingKey, shape: Any, default: Any, description: str) -> SettingSpec:
    return SettingSpec(key, TypeAdapter(shape), default, description)


# Los defaults son los de §6.11. Los datos de transferencia salen vacíos a
# propósito: no hay que mostrarle a un cliente un CBU inventado.
SPECS: dict[SettingKey, SettingSpec] = {
    spec.key: spec
    for spec in (
        _spec(
            SettingKey.SHIFT_DEFAULT,
            ShiftDefault,
            {
                "open": "08:00",
                "close": "12:00",
                "prep_eta": "12:15",
                "dispatch_eta": "12:30",
                "cancel_window_min": 20,
                "weekdays": [1, 2, 3, 4, 5],
            },
            "Plantilla del turno diario: horarios, ventana de cancelación y días que se opera.",
        ),
        _spec(
            SettingKey.TIMEZONE,
            Timezone,
            "America/Argentina/Buenos_Aires",
            "Zona horaria en la que se interpretan los horarios del turno.",
        ),
        _spec(
            SettingKey.COVERAGE_MODE,
            CoverageMode,
            CoverageMode.NEIGHBORHOOD_AND_RADIUS.value,
            "Qué reglas de cobertura de entrega están activas.",
        ),
        _spec(
            SettingKey.COVERAGE_ORIGIN,
            CoverageOrigin,
            {"lat": -34.63, "lng": -58.41},
            "Punto desde el que se mide el radio de entrega.",
        ),
        _spec(
            SettingKey.SHIPPING_MODE,
            ShippingMode,
            ShippingMode.BY_DISTANCE.value,
            "Cómo se cobra el envío.",
        ),
        _spec(
            SettingKey.SHIPPING_FLAT_AMOUNT,
            Money,
            200000,
            "Costo fijo de envío, en centavos (se usa con el modo de envío fijo).",
        ),
        _spec(
            SettingKey.SHIPPING_TIERS,
            ShippingTiers,
            [
                {"max_km": 2, "amount": 100000},
                {"max_km": 4, "amount": 150000},
                {"max_km": 6, "amount": 250000},
            ],
            "Tabla de costo de envío por distancia (montos en centavos).",
        ),
        _spec(
            SettingKey.PAYMENT_TRANSFER,
            PaymentTransfer,
            {"alias": "MORFI.CENTER", "holder": "", "bank": "", "cbu": ""},
            "Datos de la cuenta a la que los clientes hacen la transferencia.",
        ),
        _spec(
            SettingKey.STOCK_RESERVATION_TTL_MIN,
            ReservationTtlMin,
            40,
            "Minutos que se le guarda el stock a un pedido sin pagar.",
        ),
        _spec(
            SettingKey.PROMO_TIE_BREAKER,
            PromoTieBreaker,
            PromoTieBreaker.LOWEST_PRICE.value,
            "Qué promo gana cuando hay varias vigentes a la vez.",
        ),
        _spec(
            SettingKey.ORDERS_CODE_PREFIX,
            OrderCodePrefix,
            "MC",
            "Prefijo del código de cada pedido (hasta 6 letras o números en mayúscula).",
        ),
    )
}

# Cómo se le explica al admin cada tipo de error de Pydantic. Lo que no esté
# acá cae al mensaje original (en inglés) en vez de perderse.
_ERROR_MESSAGES = {
    "missing": "Es obligatorio.",
    "extra_forbidden": "Este campo no existe.",
    "int_type": "Tiene que ser un número entero.",
    "int_parsing": "Tiene que ser un número entero.",
    "float_type": "Tiene que ser un número.",
    "string_type": "Tiene que ser un texto.",
    "list_type": "Tiene que ser una lista.",
    "model_type": "Tiene que ser un objeto con sus campos.",
    "too_short": "No puede estar vacío.",
    "string_too_short": "No puede estar vacío.",
    "string_pattern_mismatch": "Formato inválido.",
    "enum": "Valor no permitido.",
}


def _explain(error: dict[str, Any]) -> str:
    kind = error["type"]
    ctx = error.get("ctx") or {}
    if kind in ("greater_than_equal", "less_than_equal", "greater_than", "less_than"):
        wording = {
            "greater_than_equal": "mayor o igual a",
            "less_than_equal": "menor o igual a",
            "greater_than": "mayor que",
            "less_than": "menor que",
        }[kind]
        limit = next(iter(ctx.values()), "")
        return f"Tiene que ser {wording} {limit}."
    if kind == "enum":
        options = str(ctx.get("expected", "")).replace(" or ", " o ")
        return f"Valor no permitido. Opciones: {options}."
    if kind in _ERROR_MESSAGES:
        return _ERROR_MESSAGES[kind]
    return error["msg"].removeprefix("Value error, ")


def _fields(exc: ValidationError) -> list[dict[str, str]]:
    return [
        {
            "field": ".".join(str(part) for part in error["loc"]) or "value",
            "message": _explain(error),
        }
        for error in exc.errors()
    ]


class SettingsService:
    """Lee y escribe la configuración del negocio sabiendo qué claves existen,
    qué forma tiene cada una y con qué valor arrancan.

    Una clave que nunca se guardó devuelve su default: el sistema anda desde el
    primer día, antes de que nadie toque el panel de admin.
    """

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = SettingsRepository(session)

    # ---------- lectura ----------

    def get(self, key: SettingKey) -> Any:
        """El valor ya validado y tipado (modelos, enums, ints), o el default."""
        spec = SPECS[key]
        stored = self.repo.get_typed(key.value)
        try:
            raw = spec.default if stored is None else self.repo.get(key.value)
            return spec.adapter.validate_python(raw)
        except ValueError as exc:  # JSON roto o forma inválida (ValidationError es ValueError)
            raise SettingCorruptError(
                f"La configuración «{key.value}» guardada no es válida.",
                {"key": key.value},
            ) from exc

    def get_shift_default(self) -> ShiftDefault:
        return self.get(SettingKey.SHIFT_DEFAULT)

    def get_timezone(self) -> str:
        return self.get(SettingKey.TIMEZONE)

    def get_coverage_mode(self) -> CoverageMode:
        return self.get(SettingKey.COVERAGE_MODE)

    def get_coverage_origin(self) -> CoverageOrigin:
        return self.get(SettingKey.COVERAGE_ORIGIN)

    def get_shipping_mode(self) -> ShippingMode:
        return self.get(SettingKey.SHIPPING_MODE)

    def get_shipping_flat_amount(self) -> int:
        return self.get(SettingKey.SHIPPING_FLAT_AMOUNT)

    def get_shipping_tiers(self) -> list[ShippingTier]:
        return self.get(SettingKey.SHIPPING_TIERS)

    def get_payment_transfer(self) -> PaymentTransfer:
        return self.get(SettingKey.PAYMENT_TRANSFER)

    def get_stock_reservation_ttl_min(self) -> int:
        return self.get(SettingKey.STOCK_RESERVATION_TTL_MIN)

    def get_promo_tie_breaker(self) -> PromoTieBreaker:
        return self.get(SettingKey.PROMO_TIE_BREAKER)

    def get_order_code_prefix(self) -> str:
        return self.get(SettingKey.ORDERS_CODE_PREFIX)

    def list_settings(self) -> list[SettingView]:
        """Las 11 claves, guardadas o no: el panel de admin ve el set completo
        desde el primer día, con `is_default` marcando las que nadie tocó.

        Devuelve el valor tal como está guardado, **sin validarlo**: si una
        quedó corrupta (`SETTING_CORRUPT` al leerla), el admin tiene que poder
        verla y pisarla desde acá en vez de quedar trabado.
        """
        return [self._view(spec) for spec in SPECS.values()]

    def view(self, key: str) -> SettingView:
        return self._view(self._spec_for(key))

    def _view(self, spec: SettingSpec) -> SettingView:
        row = self.repo.get_typed(spec.key.value)
        if row is None:
            return SettingView(
                key=spec.key.value,
                value=spec.default,
                value_type=infer_value_type(spec.default),
                description=spec.description,
                is_default=True,
                updated_at=None,
                updated_by=None,
            )
        try:
            stored_value = json.loads(row.value)
        except ValueError:
            stored_value = row.value  # ni JSON es: se muestra el texto crudo para poder repararlo
        return SettingView(
            key=spec.key.value,
            value=stored_value,
            value_type=row.value_type,
            description=spec.description,
            is_default=False,
            updated_at=row.updated_at,
            updated_by=row.updated_by,
        )

    # ---------- escritura ----------

    def set(
        self, key: str, value: Any, actor: User | None = None, *, ip: str | None = None
    ) -> SettingView:
        """Valida `value` contra la forma de `key` y lo guarda, dejando rastro
        en `audit_log` con el valor anterior y el nuevo.

        Lo que se guarda es la forma canónica que devuelve la validación (sin
        espacios sobrantes, `weekdays` ordenados...), no lo que llegó tal cual.
        Si el valor resultante es el que ya regía, no se escribe ni se audita
        nada: un PUT que no cambia nada no debe ensuciar el historial.
        """
        spec = self._spec_for(key)
        try:
            validated = spec.adapter.validate_python(value)
        except ValidationError as exc:
            raise DomainValidationError(INVALID_VALUE, {"fields": _fields(exc)}) from exc
        canonical = spec.adapter.dump_python(validated, mode="json")

        before = self._view(spec).value
        if canonical != before:
            self.repo.set(spec.key.value, canonical, actor, description=spec.description)
            self.session.add(
                AuditLog(
                    actor_id=actor.id if actor else None,
                    action="setting.update",
                    entity_type="setting",
                    entity_id=spec.key.value,
                    data=json.dumps({"before": before, "after": canonical}, ensure_ascii=False),
                    ip=ip,
                )
            )
            self.session.flush()
        return self._view(spec)

    def _spec_for(self, key: str) -> SettingSpec:
        try:
            return SPECS[SettingKey(key)]
        except ValueError:
            raise NotFoundError(UNKNOWN_KEY, {"key": key}) from None
