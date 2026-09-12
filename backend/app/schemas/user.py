"""Schemas de usuario."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import Role, UserStatus, VehicleType


class RegisterIn(BaseModel):
    """Alta de cuenta propia. La forma exacta de cada campo la valida
    ``user_service`` (mensajes más claros que la validación genérica de
    Pydantic); acá solo se ponen límites razonables para no aceptar basura."""

    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    email: str = Field(min_length=3, max_length=255)
    phone: str | None = Field(default=None, max_length=30)
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    """Vista pública de un usuario — nunca incluye ``password_hash``."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    first_name: str
    last_name: str
    email: str
    phone: str | None
    role: Role
    status: UserStatus


class UpdateProfileIn(BaseModel):
    """PATCH parcial de perfil: solo se tocan los campos presentes en el
    body (ver ``UserService.update_profile``). ``email`` no es editable acá."""

    first_name: str | None = Field(default=None, max_length=80)
    last_name: str | None = Field(default=None, max_length=80)
    phone: str | None = Field(default=None, max_length=30)


class MeOut(BaseModel):
    """Respuesta de `GET /auth/me`: datos del usuario logueado + su saldo a
    favor (centavos). No incluye `status` — si la cuenta no está `ACTIVE`,
    `get_current_user` ya rechazó la request con 401 antes de llegar acá."""

    id: int
    first_name: str
    last_name: str
    email: str
    phone: str | None
    role: Role
    balance: int


class CreateStaffIn(BaseModel):
    """Alta de personal (`role` debe ser `ADMIN` o `DELIVERY`) hecha por un
    admin. `password` es opcional: si no se manda, se genera una temporal
    (ver `AuthService.create_staff`). `vehicle_type`/`capacity` solo aplican
    a `DELIVERY`."""

    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    email: str = Field(min_length=3, max_length=255)
    phone: str | None = Field(default=None, max_length=30)
    role: Role
    password: str | None = Field(default=None, min_length=1, max_length=128)
    vehicle_type: VehicleType | None = None
    capacity: int | None = Field(default=None, ge=1)


class CreateStaffOut(UserOut):
    """`UserOut` + la contraseña temporal generada (solo si `password` no
    vino en el request; si el admin la definió, viaja `null` — no se repite
    lo que el admin ya escribió)."""

    temporary_password: str | None


class UserListOut(BaseModel):
    """Paginado estándar (§11 de `02_Documento_Tecnico.md`): `{items, page, page_size, total}`."""

    items: list[UserOut]
    page: int
    page_size: int
    total: int


class UpdateUserIn(BaseModel):
    """`PATCH /users/{id}` (admin): edita `role` y/o `status` de otro
    usuario. Al menos uno de los dos tiene que venir."""

    role: Role | None = None
    status: UserStatus | None = None


__all__ = [
    "RegisterIn",
    "UserOut",
    "UpdateProfileIn",
    "MeOut",
    "CreateStaffIn",
    "CreateStaffOut",
    "UserListOut",
    "UpdateUserIn",
]
