"""Acceso a datos de `system_settings` (ver `app/models/settings.py`).

El valor siempre se guarda y se lee como JSON — `value_type` es metadata
para validar/mostrar, no un códec distinto (ver el docstring del modelo).
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.core.enums import SettingValueType
from app.models.settings import SystemSetting

_INFER_VALUE_TYPE: dict[type, SettingValueType] = {
    bool: SettingValueType.BOOL,
    int: SettingValueType.INT,
    str: SettingValueType.STRING,
}


def _infer_value_type(value: Any) -> SettingValueType:
    """`bool` antes que `int` a propósito: en Python `bool` es subclase de
    `int`, y una clave booleana no debería inferirse como `int`."""
    for py_type, setting_type in _INFER_VALUE_TYPE.items():
        if isinstance(value, py_type):
            return setting_type
    return SettingValueType.JSON


class SettingsRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, key: str, default: Any = None) -> Any:
        """Devuelve el valor ya decodificado de JSON, o `default` si la
        clave no existe."""
        row = self.session.get(SystemSetting, key)
        if row is None:
            return default
        return json.loads(row.value)

    def get_typed(self, key: str, expected_type: type, default: Any = None) -> Any:
        """Como `get`, pero valida que el valor decodificado sea del tipo
        esperado.

        :raises TypeError: si la clave existe pero su valor no es una
            instancia de `expected_type` (dato corrupto o cargado a mano).
        """
        row = self.session.get(SystemSetting, key)
        if row is None:
            return default
        value = json.loads(row.value)
        if not isinstance(value, expected_type):
            raise TypeError(
                f"system_settings[{key!r}] es {type(value).__name__}, "
                f"se esperaba {expected_type.__name__}."
            )
        return value

    def set(
        self,
        key: str,
        value: Any,
        *,
        actor_id: int | None = None,
        value_type: SettingValueType | None = None,
        description: str | None = None,
    ) -> SystemSetting:
        """Crea o actualiza una clave (upsert). `value_type` se infiere del
        tipo de `value` si no se pasa explícitamente."""
        row = self.session.get(SystemSetting, key)
        resolved_type = value_type or _infer_value_type(value)
        encoded = json.dumps(value)

        if row is None:
            row = SystemSetting(
                key=key,
                value=encoded,
                value_type=resolved_type,
                description=description,
                updated_by=actor_id,
            )
            self.session.add(row)
        else:
            row.value = encoded
            row.value_type = resolved_type
            if description is not None:
                row.description = description
            row.updated_by = actor_id

        self.session.flush()
        return row


__all__ = ["SettingsRepository"]
