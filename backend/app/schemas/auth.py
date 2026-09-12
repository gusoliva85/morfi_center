"""Schemas del flujo de autenticación (login/registro) y sus respuestas."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.user import UserOut


class LoginIn(BaseModel):
    """Credenciales de login local. La forma exacta del email la valida
    ``user_service.normalize_email`` dentro de ``AuthService.authenticate``."""

    email: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class AuthOut(BaseModel):
    """Respuesta de login/registro: access token + datos del usuario.

    El refresh token **no** va acá — viaja en una cookie httpOnly, nunca en
    el cuerpo de la respuesta.
    """

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class LogoutOut(BaseModel):
    """Respuesta de logout. Siempre `ok: true` — cerrar sesión no falla."""

    ok: bool = True


class ForgotPasswordIn(BaseModel):
    email: str = Field(min_length=1, max_length=255)


class ForgotPasswordOut(BaseModel):
    """Siempre `ok: true`, exista o no una cuenta con ese email — no lo revela."""

    ok: bool = True


class ResetPasswordIn(BaseModel):
    token: str = Field(min_length=1)
    password: str = Field(min_length=1, max_length=128)


class ResetPasswordOut(BaseModel):
    ok: bool = True


__all__ = [
    "LoginIn",
    "AuthOut",
    "LogoutOut",
    "ForgotPasswordIn",
    "ForgotPasswordOut",
    "ResetPasswordIn",
    "ResetPasswordOut",
]
