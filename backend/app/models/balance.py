"""Saldo a favor del cliente.

Solo la tabla `customer_balances` por ahora (1:1 con `User`); los movimientos
(`BalanceTransaction`, `balance_transactions`) se agregan en la Fase 12 junto
con las cancelaciones. Ver ``documentacion/02_Documento_Tecnico.md`` §6.8.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.timezone import now_utc
from app.db.base import Base
from app.db.types import UtcDateTime

if TYPE_CHECKING:
    from app.models.user import User


class CustomerBalance(Base):
    """Saldo a favor acumulado de un cliente (crédito por cancelaciones, §21).

    ``user_id`` es a la vez PK y FK: un saldo por usuario. Arranca en 0.
    """

    __tablename__ = "customer_balances"
    # Nombre corto: la convención de MetaData ya antepone "ck_<tabla>_" (ver db/base.py).
    __table_args__ = (CheckConstraint("balance >= 0", name="balance_non_negative"),)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    balance: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # centavos
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime, default=now_utc, onupdate=now_utc, nullable=False
    )

    user: Mapped[User] = relationship(back_populates="balance")

    def __repr__(self) -> str:  # pragma: no cover
        return f"CustomerBalance(user_id={self.user_id!r}, balance={self.balance!r})"


__all__ = ["CustomerBalance"]
