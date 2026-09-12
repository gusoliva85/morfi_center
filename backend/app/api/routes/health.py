"""Endpoint de salud del servicio."""

from __future__ import annotations

from fastapi import APIRouter

from app import __version__
from app.core.config import settings

router = APIRouter(tags=["infra"])


@router.get("/health", summary="Estado del servicio")
def health() -> dict[str, str]:
    """Chequeo simple de que la API está viva."""
    return {
        "status": "ok",
        "env": settings.app_env,
        "app": settings.app_name,
        "version": __version__,
    }
