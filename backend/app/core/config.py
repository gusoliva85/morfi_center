from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_DEFAULT_JWT_SECRET = "dev-only-insecure-secret-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_env: Literal["development", "production"] = "development"
    app_name: str = "Morfi Center"
    app_timezone: str = "America/Argentina/Buenos_Aires"
    api_prefix: str = "/api/v1"
    frontend_origin: str = "http://localhost:5500"
    cookie_samesite: Literal["lax", "none", "strict"] = "lax"

    # DB
    database_url: str = "sqlite:///./data/morfi.db"

    # Auth
    jwt_secret: str = _INSECURE_DEFAULT_JWT_SECRET
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    password_reset_minutes: int = 30

    # Admin inicial de producción (solo variables de entorno del servidor,
    # nunca en el repositorio): sin esto no hay forma de crear el primer
    # admin, porque POST /users exige ya ser admin.
    seed_admin_email: str = ""
    seed_admin_password: str = ""

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/v1/auth/google/callback"

    # Servicios externos
    geocoding_provider: Literal["nominatim", "google"] = "nominatim"
    nominatim_user_agent: str = "morfi-center-dev"
    google_maps_api_key: str = ""
    route_provider: Literal["manual", "osrm", "google"] = "manual"

    # Storage
    storage_dir: str = "./storage"
    max_upload_mb: int = 8

    # Turnos y reservas
    reservation_ttl_min: int = 40

    @field_validator("jwt_secret")
    @classmethod
    def _jwt_secret_must_be_real_in_production(cls, v: str, info) -> str:
        app_env = info.data.get("app_env", "development")
        if app_env == "production" and (not v or v == _INSECURE_DEFAULT_JWT_SECRET):
            raise ValueError(
                "JWT_SECRET debe configurarse con un valor real en producción "
                "(backend/.env en el VPS, nunca en git)."
            )
        return v


settings = Settings()
