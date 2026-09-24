"""La forma que debe tener el valor de cada clave de `system_settings` (§6.11).

Todo es estricto (`"40"` no es un `40`, `true` no es un `1`) y los objetos
rechazan campos de más: un error de tipeo en el panel de admin tiene que
fallar al guardar, no descubrirse el día que llega un pedido.
"""

from datetime import datetime
from typing import Annotated, Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StrictFloat,
    StrictInt,
    StrictStr,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.core.enums import SettingValueType

Number = StrictInt | StrictFloat


def _check_hhmm(value: str) -> str:
    hour, sep, minute = value.partition(":")
    ok = (
        sep == ":"
        and len(hour) == 2
        and len(minute) == 2
        and hour.isdigit()
        and minute.isdigit()
        and int(hour) < 24
        and int(minute) < 60
    )
    if not ok:
        raise ValueError("Debe tener formato HH:MM (por ejemplo 08:00).")
    return value


def _minutes(hhmm: str) -> int:
    hour, minute = hhmm.split(":")
    return int(hour) * 60 + int(minute)


def _check_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError, OSError) as exc:
        raise ValueError("No es una zona horaria válida (por ejemplo America/Montevideo).") from exc
    return value


HHMM = Annotated[StrictStr, AfterValidator(_check_hhmm)]
Timezone = Annotated[StrictStr, AfterValidator(_check_timezone)]
Money = Annotated[StrictInt, Field(ge=0)]  # centavos, como todo el dinero del sistema


def _check_code_prefix(value: str) -> str:
    if not (
        1 <= len(value) <= 6 and value.isascii() and value.isalnum() and value.upper() == value
    ):
        raise ValueError("Entre 1 y 6 letras mayúsculas o números, sin espacios (por ejemplo MC).")
    return value


OrderCodePrefix = Annotated[StrictStr, AfterValidator(_check_code_prefix)]
ReservationTtlMin = Annotated[StrictInt, Field(ge=1)]


class _Shape(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ShiftDefault(_Shape):
    """Plantilla con la que se crea el turno de cada día. `weekdays` usa la
    numeración ISO: 1 = lunes ... 7 = domingo."""

    open: HHMM
    close: HHMM
    prep_eta: HHMM | None = None
    dispatch_eta: HHMM | None = None
    cancel_window_min: Annotated[StrictInt, Field(ge=0)]
    weekdays: Annotated[list[Annotated[StrictInt, Field(ge=1, le=7)]], Field(min_length=1)]

    @field_validator("weekdays")
    @classmethod
    def _no_repeated_days(cls, v: list[int]) -> list[int]:
        if len(set(v)) != len(v):
            raise ValueError("Hay días repetidos.")
        return sorted(v)

    @model_validator(mode="after")
    def _coherent_schedule(self) -> "ShiftDefault":
        duration = _minutes(self.close) - _minutes(self.open)
        if duration <= 0:
            raise ValueError("La hora de cierre debe ser posterior a la de apertura.")
        if self.cancel_window_min > duration:
            raise ValueError("La ventana de cancelación no puede ser más larga que el turno.")
        return self


class CoverageOrigin(_Shape):
    lat: Annotated[Number, Field(ge=-90, le=90)]
    lng: Annotated[Number, Field(ge=-180, le=180)]


class ShippingTier(_Shape):
    max_km: Annotated[Number, Field(gt=0)]
    amount: Money


def _ascending_tiers(tiers: list[ShippingTier]) -> list[ShippingTier]:
    kms = [tier.max_km for tier in tiers]
    if any(later <= earlier for earlier, later in zip(kms, kms[1:], strict=False)):
        raise ValueError("Los rangos deben ir de menor a mayor distancia, sin repetir.")
    return tiers


ShippingTiers = Annotated[list[ShippingTier], Field(min_length=1), AfterValidator(_ascending_tiers)]


class PaymentTransfer(_Shape):
    alias: Annotated[StrictStr, StringConstraints(strip_whitespace=True, min_length=1)]
    holder: Annotated[StrictStr, StringConstraints(strip_whitespace=True)]
    bank: Annotated[StrictStr, StringConstraints(strip_whitespace=True)]
    cbu: Annotated[StrictStr, StringConstraints(strip_whitespace=True)]

    @field_validator("cbu")
    @classmethod
    def _cbu_has_22_digits(cls, v: str) -> str:
        # Vacío se permite: hasta que el admin cargue el dato real. Si hay algo,
        # tiene que ser un CBU/CVU (22 dígitos): los clientes van a transferir ahí.
        if v and not (v.isdigit() and len(v) == 22):
            raise ValueError("El CBU/CVU debe tener 22 dígitos.")
        return v


class SettingOut(BaseModel):
    """Una configuración para el panel de admin. `value` es JSON libre porque
    cada clave tiene su propia forma; `is_default` dice si rige el valor por
    defecto (nadie la guardó todavía)."""

    model_config = ConfigDict(from_attributes=True)

    key: str
    value: Any
    value_type: SettingValueType
    description: str
    is_default: bool
    updated_at: datetime | None
    updated_by: int | None


class SettingListOut(BaseModel):
    items: list[SettingOut]


class SettingUpdateIn(BaseModel):
    """`{"value": ...}`: la forma del valor la valida el servicio, según la clave."""

    value: Any
