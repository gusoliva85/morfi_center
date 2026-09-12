"""Agregador de modelos SQLAlchemy.

Importar este módulo debe registrar **todos** los modelos en ``Base.metadata``
(lo usan el autogenerate de Alembic y ``create_all`` en los tests).

Se agrega una línea de import por cada módulo de modelos a medida que avanzan las
fases del roadmap.
"""

from __future__ import annotations

from app.db.base import Base

# --- Modelos por dominio (se completa fase a fase) ---
from app.models.audit import AuditLog  # Fase 1 (auditoría de cambios de rol/estado)
from app.models.balance import CustomerBalance  # Fase 1 (vacío; lógica en Fase 12)
from app.models.cart import Cart  # Fase 1 (vacío; lógica en Fase 6)
from app.models.settings import SystemSetting  # Fase 2 (Tema 2.1)
from app.models.shift import Shift  # Fase 2 (Tema 2.2)
from app.models.token import RevokedToken  # Fase 1 (rotación de refresh tokens)
from app.models.user import User, UserAuthProvider, UserProfile  # Fase 1

# ...

__all__ = [
    "Base",
    "User",
    "UserAuthProvider",
    "UserProfile",
    "Cart",
    "CustomerBalance",
    "RevokedToken",
    "AuditLog",
    "SystemSetting",
    "Shift",
]
