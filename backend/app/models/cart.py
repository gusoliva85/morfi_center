"""Carrito del cliente.

Solo la tabla `carts` por ahora (1:1 con `User`); los ítems (`CartItem`,
`cart_items`) se agregan en la Fase 6 cuando llega la lógica de armado de
pedido. Ver ``documentacion/02_Documento_Tecnico.md`` §6.5.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.timezone import now_utc
from app.db.base import Base
from app.db.types import UtcDateTime

if TYPE_CHECKING:
    from app.models.user import User


class Cart(Base):
    """Carrito activo de un usuario. Uno por usuario (1:1, `user_id` único)."""

    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime, default=now_utc, onupdate=now_utc, nullable=False
    )

    user: Mapped[User] = relationship(back_populates="cart")

    def __repr__(self) -> str:  # pragma: no cover
        return f"Cart(id={self.id!r}, user_id={self.user_id!r})"


__all__ = ["Cart"]
