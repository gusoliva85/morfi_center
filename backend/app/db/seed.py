"""Datos semilla del entorno de desarrollo (idempotente).

Ejecutar (desde ``backend/``, con las migraciones aplicadas)::

    python -m app.db.seed

Cada fase del roadmap agrega su parte dentro de :func:`run_seed`. Todo tiene que
poder correrse varias veces sin duplicar datos: usar :func:`get_or_create` o
chequear la existencia antes de insertar.
"""

from __future__ import annotations

import logging
from typing import Any, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import Role, VehicleType
from app.core.logging import configure_logging
from app.db.session import session_scope
from app.models.settings import SystemSetting
from app.repositories.settings_repository import SettingsRepository
from app.services.auth_service import AuthService
from app.services.settings_service import SETTINGS_DEFAULTS

logger = logging.getLogger("morfi.seed")

_M = TypeVar("_M")

# Credenciales de prueba documentadas en `documentacion/Usuarios.md` — de
# desarrollo únicamente, nunca se usan en producción (no hay seed ahí).
SEED_ADMIN_EMAIL = "admin@morficenter.test"
SEED_ADMIN_PASSWORD = "admin123"
SEED_CUSTOMER_EMAIL = "cliente@morficenter.test"
SEED_CUSTOMER_PASSWORD = "cliente123"
SEED_DELIVERY_EMAIL = "delivery@morficenter.test"
SEED_DELIVERY_PASSWORD = "delivery123"


def get_or_create(
    session: Session,
    model: type[_M],
    *,
    defaults: dict[str, Any] | None = None,
    **filters: Any,
) -> tuple[_M, bool]:
    """Devuelve ``(instancia, creada?)``.

    Busca una fila que cumpla ``filters``; si no existe la crea con
    ``filters + defaults`` y hace ``flush`` (para tener el id disponible).
    """
    instance = session.scalars(select(model).filter_by(**filters)).first()
    if instance is not None:
        return instance, False
    instance = model(**{**filters, **(defaults or {})})
    session.add(instance)
    session.flush()
    return instance, True


def seed_users(session: Session) -> None:
    """Usuarios de prueba: ADMIN, CUSTOMER y DELIVERY (`03_Roadmap.md` T-1.10.1).

    Credenciales documentadas en `documentacion/Usuarios.md`. Idempotente:
    si el email ya existe, no hace nada (chequea antes de crear en vez de
    usar `get_or_create`, porque el alta de cada rol es multi-paso —
    `AuthService.register`/`.create_staff` ya arman usuario + provider +
    lo que corresponda según el rol).
    """
    auth = AuthService(session)

    if auth.users.get_by_email(SEED_ADMIN_EMAIL) is None:
        auth.create_staff(
            first_name="Admin",
            last_name="Morfi",
            email=SEED_ADMIN_EMAIL,
            role=Role.ADMIN,
            password=SEED_ADMIN_PASSWORD,
        )
        logger.info("Seed: usuario ADMIN de prueba creado (%s)", SEED_ADMIN_EMAIL)

    if auth.users.get_by_email(SEED_CUSTOMER_EMAIL) is None:
        auth.register(
            first_name="Cliente",
            last_name="Morfi",
            email=SEED_CUSTOMER_EMAIL,
            password=SEED_CUSTOMER_PASSWORD,
        )
        logger.info("Seed: usuario CUSTOMER de prueba creado (%s)", SEED_CUSTOMER_EMAIL)

    if auth.users.get_by_email(SEED_DELIVERY_EMAIL) is None:
        auth.create_staff(
            first_name="Delivery",
            last_name="Morfi",
            email=SEED_DELIVERY_EMAIL,
            role=Role.DELIVERY,
            password=SEED_DELIVERY_PASSWORD,
            vehicle_type=VehicleType.MOTO,
            capacity=3,
        )
        logger.info("Seed: usuario DELIVERY de prueba creado (%s)", SEED_DELIVERY_EMAIL)


def seed_settings(session: Session) -> None:
    """Defaults de `system_settings` para toda clave conocida que todavía no
    tenga un valor guardado (`03_Roadmap.md` T-2.1.4, defaults de
    `02_Documento_Tecnico.md §6.11`).

    Idempotente por clave: si un admin ya la configuró (vía la API), el
    seed no la pisa — solo completa las que faltan.
    """
    repo = SettingsRepository(session)
    for key, default_value in SETTINGS_DEFAULTS.items():
        if session.get(SystemSetting, key.value) is None:
            repo.set(key.value, default_value)
            logger.info("Seed: system_settings[%s] = default", key.value)


def run_seed(session: Session) -> None:
    """Carga los datos de prueba. Se completa fase a fase.

    El orden final se ajusta según dependencias (p. ej. ``system_settings`` antes
    de lo que las lee).
    """
    # Fase 2 · configuración y turno del día
    seed_settings(session)
    #   seed_today_shift(session)
    seed_users(session)
    # Fase 3 · catálogo demo (categorías + productos + stock)
    #   seed_catalog(session)
    # Fase 5 · promoción + plato del día
    #   seed_promotions(session)
    # Fase 7 · cobertura (origen, barrios, radio)
    #   seed_coverage(session)
    # Fase 14 · repartidores de prueba adicionales (el DELIVERY base ya lo crea seed_users)
    #   seed_drivers(session)


def main() -> None:
    configure_logging()
    logger.info("Seed · inicio")
    with session_scope() as session:
        run_seed(session)
    logger.info("Seed · fin")


if __name__ == "__main__":
    main()
