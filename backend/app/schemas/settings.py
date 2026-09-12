"""Schemas de configuración del sistema (`system_settings`, Tema 2.1)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, RootModel


class SettingsOut(RootModel[dict[str, Any]]):
    """`GET /settings`: valor efectivo (guardado, o el default de §6.11) de
    cada clave conocida — `{"timezone": "...", "shift.default": {...}, ...}`."""


class UpdateSettingIn(BaseModel):
    value: Any


class UpdateSettingOut(BaseModel):
    key: str
    value: Any


__all__ = ["SettingsOut", "UpdateSettingIn", "UpdateSettingOut"]
