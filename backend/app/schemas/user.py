from pydantic import BaseModel, ConfigDict, field_validator

from app.core.enums import Role
from app.services.user_service import is_valid_name


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
