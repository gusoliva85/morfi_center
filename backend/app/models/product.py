from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import TimestampMixin
from app.models.category import Category


class Product(TimestampMixin, Base):
    """Producto del catálogo (§6.3). `base_price` está en **centavos** y es
    siempre mayor que cero (lo exige también la base, no solo el código). Un
    producto inactivo, o de una categoría inactiva, no se muestra al público."""

    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("base_price > 0", name="price_positive"),
        Index("ix_products_category_id", "category_id"),
        Index("ix_products_is_active", "is_active"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # Sin ON DELETE CASCADE: borrar una categoría con productos tiene que fallar,
    # no llevarse el catálogo puesto (las categorías se desactivan, no se borran).
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    base_price: Mapped[int] = mapped_column(Integer, nullable=False)  # centavos
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    category: Mapped[Category] = relationship()
    images: Mapped[list["ProductImage"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="(ProductImage.sort_order, ProductImage.id)",
    )


class ProductImage(Base):
    """Imagen de un producto. `path` es relativo a `storage/` (o `assets/`);
    a lo sumo una es la principal (`is_primary`), cosa que garantiza la carga de
    imágenes en `T-3.2.5`."""

    __tablename__ = "product_images"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    path: Mapped[str] = mapped_column(String, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    product: Mapped[Product] = relationship(back_populates="images")
