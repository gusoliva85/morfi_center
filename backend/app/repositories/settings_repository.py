import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import SettingValueType
from app.models import SystemSetting, User


def infer_value_type(value: Any) -> SettingValueType:
    # bool antes que int: en Python `isinstance(True, int)` es True.
    if isinstance(value, bool):
        return SettingValueType.BOOL
    if isinstance(value, int):
        return SettingValueType.INT
    if isinstance(value, str):
        return SettingValueType.STRING
    return SettingValueType.JSON  # dict, list, float, None, ...


class SettingsRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, key: str, default: Any = None) -> Any:
        """Valor ya decodificado, o `default` si la clave no existe."""
        row = self.session.get(SystemSetting, key)
        if row is None:
            return default
        return json.loads(row.value)

    def get_typed(self, key: str) -> SystemSetting | None:
        """La fila completa (valor + `value_type` + metadata), no solo el
        valor — la usa la API para exponer de qué tipo es cada setting sin
        que quien la llama tenga que adivinarlo."""
        return self.session.get(SystemSetting, key)

    def list_all(self) -> list[SystemSetting]:
        return list(self.session.scalars(select(SystemSetting).order_by(SystemSetting.key)))

    def set(
        self,
        key: str,
        value: Any,
        actor: User | None = None,
        *,
        description: str | None = None,
    ) -> SystemSetting:
        """Crea o actualiza una clave. `value` es un valor de Python común
        (dict, list, str, int, bool) — el repositorio se encarga de
        serializarlo y de inferir su `value_type`."""
        row = self.session.get(SystemSetting, key)
        if row is None:
            row = SystemSetting(key=key, description=description)
            self.session.add(row)
        elif description is not None:
            row.description = description

        row.value = json.dumps(value)
        row.value_type = infer_value_type(value)
        row.updated_by = actor.id if actor else None
        self.session.flush()
        return row
