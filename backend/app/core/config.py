"""Configuración central de Morfi Center.

Lee variables de entorno (y de ``backend/.env`` si existe) y expone un único
objeto :data:`settings` que se importa desde el resto de la aplicación.

Los comandos del proyecto (``uvicorn``, ``alembic``, ``pytest``, ``iniciar.bat``)
se ejecutan siempre desde la carpeta ``backend/``; por eso las rutas relativas
por defecto (``./data``, ``./storage``) resuelven ahí.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/  (este archivo está en backend/app/core/config.py)
BASE_DIR: Path = Path(__file__).resolve().parents[2]

# Valor por defecto SOLO para desarrollo. En producción es obligatorio
# definir JWT_SECRET en backend/.env (ver validación en model_post_init).
_INSECURE_DEV_SECRET = "dev-insecure-secret-change-me-0000000000000000000000000000000000"


class Settings(BaseSettings):
    """Configuración de la aplicación. Cada atributo se puede sobreescribir
    con la variable de entorno del mismo nombre en mayúsculas."""

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ────────────────────────────────────────────────
    app_env: Literal["development", "production"] = "development"
    app_name: str = "Morfi Center"
    app_timezone: str = "America/Argentina/Buenos_Aires"
    api_prefix: str = "/api/v1"
    frontend_origin: str = "http://localhost:5500"

    # ── Base de datos ─────────────────────────────────────
    database_url: str = "sqlite:///./data/morfi.db"

    # ── Auth / JWT ────────────────────────────────────────
    jwt_secret: str = _INSECURE_DEV_SECRET
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    password_reset_token_minutes: int = 30

    # ── Google OAuth ──────────────────────────────────────
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/v1/auth/google/callback"

    # ── Servicios externos ────────────────────────────────
    geocoding_provider: Literal["nominatim", "google"] = "nominatim"
    nominatim_user_agent: str = "morfi-center-dev"
    google_maps_api_key: str = ""
    route_provider: Literal["manual", "osrm", "google"] = "manual"

    # ── Almacenamiento de archivos ────────────────────────
    storage_dir: str = "./storage"
    max_upload_mb: int = 8

    # ── Tareas programadas ────────────────────────────────
    reservation_ttl_min: int = 40

    # ── Derivados ─────────────────────────────────────────
    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def storage_path(self) -> Path:
        """Ruta absoluta de la carpeta de storage."""
        p = Path(self.storage_dir)
        return p if p.is_absolute() else (BASE_DIR / p).resolve()

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def cors_origins(self) -> list[str]:
        """Orígenes permitidos por CORS. En producción el front se sirve desde
        el mismo origen que la API, así que la lista puede quedar vacía."""
        return [] if self.is_production else [self.frontend_origin]

    def model_post_init(self, __context: Any) -> None:  # noqa: D401
        if self.is_production and self.jwt_secret == _INSECURE_DEV_SECRET:
            raise ValueError(
                "JWT_SECRET sin configurar: definí un valor seguro en backend/.env "
                'cuando APP_ENV=production (ej: python -c "import secrets; '
                'print(secrets.token_hex(32))").'
            )


@lru_cache
def get_settings() -> Settings:
    """Devuelve la instancia única de Settings (cacheada)."""
    return Settings()


settings: Settings = get_settings()
