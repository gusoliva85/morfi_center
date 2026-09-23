from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.core.enums import Role, VehicleType
from app.services.user_service import (
    is_valid_email,
    is_valid_name,
    validate_password,
)


class UserOut(BaseModel):
    """Usuario tal como lo ve el cliente de la API: sin `password_hash` ni
    ningún otro dato sensible."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    first_name: str
    last_name: str
    email: str
    phone: str | None
    role: Role


class StaffCreateIn(BaseModel):
    """Alta de ADMIN o DELIVERY por un admin (`POST /users`).

    `role` es un `Literal` de esos dos valores a propósito: los CUSTOMER se dan
    de alta solos por `/auth/register`, y dejar que este endpoint los cree
    abriría una vía paralela sin carrito ni saldo.
    """

    model_config = ConfigDict(extra="forbid")

    role: Literal[Role.ADMIN, Role.DELIVERY]
    first_name: str
    last_name: str
    email: str
    password: str
    phone: str | None = None
    vehicle_type: VehicleType | None = None
    capacity: int | None = None

    @field_validator("first_name", "last_name")
    @classmethod
    def _name_is_required(cls, v: str) -> str:
        if not is_valid_name(v):
            raise ValueError("Requerido.")
        return v

    @field_validator("email")
    @classmethod
    def _email_has_valid_format(cls, v: str) -> str:
        if not is_valid_email(v.strip()):
            raise ValueError("El email no tiene un formato válido.")
        return v

    @field_validator("password")
    @classmethod
    def _password_meets_the_policy(cls, v: str) -> str:
        if not validate_password(v):
            raise ValueError("Debe tener al menos 8 caracteres, con una letra y un número.")
        return v

    @field_validator("capacity")
    @classmethod
    def _capacity_is_positive(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("Debe ser mayor a 0.")
        return v

    @model_validator(mode="after")
    def _fields_match_the_role(self) -> "StaffCreateIn":
        # RF-DLV-01: el transporte es parte de los datos del repartidor (la
        # capacidad es la única explícitamente opcional).
        if self.role == Role.DELIVERY and self.vehicle_type is None:
            raise ValueError("vehicle_type es requerido para un repartidor.")
        # Un admin no reparte: aceptar estos campos guardaría datos sin sentido.
        if self.role == Role.ADMIN and (self.vehicle_type or self.capacity):
            raise ValueError("vehicle_type y capacity no aplican a un ADMIN.")
        return self


class ProfileUpdateIn(BaseModel):
    """Campos editables del perfil. Todos opcionales: se aplica solo lo que el
    cliente manda (`exclude_unset`), así editar el nombre no borra el teléfono.

    `extra="forbid"` a propósito: si alguien manda `email` o `role` esperando
    cambiarlos, tiene que enterarse con un 422 y no que se ignore en silencio,
    creyendo que se guardó algo que no se guardó.
    """

    model_config = ConfigDict(extra="forbid")

    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None

    @field_validator("first_name", "last_name")
    @classmethod
    def _name_cannot_be_blanked(cls, v: str | None) -> str | None:
        if not is_valid_name(v):
            raise ValueError("Requerido.")
        return v


class MeOut(UserOut):
    """Lo que devuelve `GET /auth/me`: el usuario más su saldo a favor, en
    centavos (§11: el dinero viaja como entero, nunca como float)."""

    balance: int

    @classmethod
    def from_user(cls, user) -> "MeOut":
        return cls(
            **UserOut.model_validate(user).model_dump(),
            # Sin fila de saldo (staff) el saldo es 0, no un error:
            # customer_balances existe solo para clientes.
            balance=user.balance.balance if user.balance else 0,
        )
