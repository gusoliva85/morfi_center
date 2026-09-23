from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.timezone import now_utc
from app.db.base import Base
from app.db.types import UTCDateTime
from app.models.user import User


class CustomerBalance(Base):
    """Saldo a favor del cliente, en centavos. Se crea en 0 junto al usuario;
    los movimientos y su lógica llegan en la Fase 12."""

    __tablename__ = "customer_balances"
    __table_args__ = (CheckConstraint("balance >= 0", name="balance_non_negative"),)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    balance: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=now_utc, onupdate=now_utc, nullable=False
    )

    user: Mapped[User] = relationship(back_populates="balance")
