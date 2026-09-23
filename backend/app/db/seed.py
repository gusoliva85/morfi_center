import logging

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.enums import Role, VehicleType
from app.db.session import SessionLocal
from app.models import User
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.user_admin_service import UserAdminService

logger = logging.getLogger(__name__)

# Usuarios de prueba, documentados en `documentacion/Usuarios.md`. Las
# contraseñas son simples y **públicas** (el repositorio lo es), así que estos
# usuarios NO se crean en producción: ver `seed_test_users`.
TEST_CUSTOMER = {
    "first_name": "Cliente",
    "last_name": "Prueba",
    "email": "cliente@morficenter.test",
    "password": "cliente1234",
    "phone": "1155550001",
}
TEST_ADMIN = {
    "role": Role.ADMIN,
    "first_name": "Admin",
    "last_name": "Prueba",
    "email": "admin@morficenter.test",
    "password": "admin1234",
    "phone": "1155550002",
}
TEST_DELIVERY = {
    "role": Role.DELIVERY,
    "first_name": "Repartidor",
    "last_name": "Prueba",
    "email": "repartidor@morficenter.test",
    "password": "repartidor1234",
    "phone": "1155550003",
    "vehicle_type": VehicleType.MOTO.value,
    "capacity": 4,
}


def seed_test_users(session: Session) -> list[User]:
    """Crea los tres usuarios de prueba. Idempotente: si ya existen, no toca nada.

    **Nunca en producción.** Sus contraseñas están documentadas en un
    repositorio público, así que crearlos en el servidor real equivale a dejar
    un admin con contraseña conocida por cualquiera.
    """
    if settings.app_env == "production":
        logger.warning(
            "Usuarios de prueba omitidos: sus contraseñas son públicas y esto es producción. "
            "Para el primer admin real, usar SEED_ADMIN_EMAIL y SEED_ADMIN_PASSWORD."
        )
        return []

    users = UserRepository(session)
    created: list[User] = []

    if users.get_by_email(TEST_CUSTOMER["email"]) is None:
        created.append(AuthService(session).register(**TEST_CUSTOMER))

    admin_service = UserAdminService(session)
    for staff in (TEST_ADMIN, TEST_DELIVERY):
        if users.get_by_email(staff["email"]) is None:
            created.append(admin_service.create_staff(**staff))

    if created:
        logger.info("Usuarios de prueba creados: %s", ", ".join(u.email for u in created))
    return created


def seed_admin_from_env(session: Session) -> User | None:
    """Crea el primer ADMIN real a partir de `SEED_ADMIN_EMAIL`/`_PASSWORD`.

    Resuelve un problema concreto de producción: `POST /users` exige ser admin,
    así que sin esto no hay forma de crear el primer admin sin tocar la base a
    mano. Las credenciales viajan por variables de entorno del servidor y no
    están en ningún archivo del repositorio.
    """
    email, password = settings.seed_admin_email, settings.seed_admin_password
    if not email or not password:
        return None

    users = UserRepository(session)
    if users.get_by_email(email) is not None:
        return None  # idempotente

    admin = UserAdminService(session).create_staff(
        role=Role.ADMIN,
        first_name="Admin",
        last_name="Morfi Center",
        email=email,
        password=password,
    )
    logger.info("Admin inicial creado desde variables de entorno: %s", admin.email)
    return admin


def run_seed(session: Session) -> None:
    """Datos semilla idempotentes (correr dos veces no duplica nada).

    Se va completando fase a fase (usuarios en Fase 1, `system_settings` en
    Fase 2, catálogo demo en Fase 3).
    """
    seed_admin_from_env(session)
    seed_test_users(session)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    session = SessionLocal()
    try:
        run_seed(session)
        session.commit()
        logger.info("Seed ejecutado correctamente.")
    finally:
        session.close()


if __name__ == "__main__":
    main()
