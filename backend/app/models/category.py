from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import TimestampMixin


class Category(TimestampMixin, Base):
    """Categoría del catálogo (§6.3). `slug` es único y se calcula al crearla
    (`catalog_service.build_category_slug`); `sort_order` es la posición en el
    menú (0, 1, 2, ...). Una categoría inactiva —y sus productos— no se muestran
    en el catálogo público."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
