from pydantic import BaseModel, field_validator

from app.schemas.user import UserOut
from app.services.user_service import is_valid_email, is_valid_name, validate_password


class RegisterIn(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str
    phone: str | None = None

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


class TokenOut(BaseModel):
    """Respuesta de registro y login (§11 del Documento Técnico). El refresh
    no va en el cuerpo: viaja en la cookie httpOnly `mc_refresh`."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut
