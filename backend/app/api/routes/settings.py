from fastapi import APIRouter, Request

from app.api.deps import AdminUser, SessionDep
from app.schemas.settings import SettingListOut, SettingOut, SettingUpdateIn
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SettingListOut)
def list_settings(admin: AdminUser, session: SessionDep) -> SettingListOut:
    """Todas las configuraciones del negocio, incluidas las que nadie guardó
    todavía (con su valor por defecto y `is_default: true`)."""
    items = SettingsService(session).list_settings()
    return SettingListOut(items=[SettingOut.model_validate(item) for item in items])


@router.put("/{key}", response_model=SettingOut)
def update_setting(
    key: str,
    data: SettingUpdateIn,
    admin: AdminUser,
    session: SessionDep,
    request: Request,
) -> SettingOut:
    """Reemplaza el valor de una configuración. Se valida contra la forma de esa
    clave y queda registrado en `audit_log` (valor anterior y nuevo)."""
    view = SettingsService(session).set(
        key,
        data.value,
        admin,
        ip=request.client.host if request.client else None,
    )
    return SettingOut.model_validate(view)
