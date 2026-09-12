"""Endpoints de configuración del sistema (Tema 2.1) — solo para admins."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.core.enums import Role
from app.core.errors import NotFoundError
from app.db.session import get_session
from app.models.user import User
from app.schemas.settings import SettingsOut, UpdateSettingIn, UpdateSettingOut
from app.services.settings_service import SettingKey, SettingsService

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SettingsOut)
def list_settings(
    _admin: User = Depends(require_role(Role.ADMIN)),
    db: Session = Depends(get_session),
) -> SettingsOut:
    """Todas las claves conocidas con su valor efectivo (guardado, o el
    default de §6.11 si todavía no se cargó)."""
    return SettingsOut(SettingsService(db).get_all())


@router.put("/{key}", response_model=UpdateSettingOut)
def update_setting(
    key: str,
    payload: UpdateSettingIn,
    admin: User = Depends(require_role(Role.ADMIN)),
    db: Session = Depends(get_session),
) -> UpdateSettingOut:
    """Actualiza una clave de configuración. Queda auditada en `audit_log`
    (`SettingsService.set`).

    :raises NotFoundError: `key` no es una de las claves conocidas.
    :raises InvalidInputError: `value` no tiene la forma esperada para esa clave.
    """
    try:
        setting_key = SettingKey(key)
    except ValueError as exc:
        raise NotFoundError("Esa clave de configuración no existe.") from exc

    validated = SettingsService(db).set(setting_key, payload.value, actor_id=admin.id)
    return UpdateSettingOut(key=setting_key.value, value=validated)


__all__ = ["router"]
