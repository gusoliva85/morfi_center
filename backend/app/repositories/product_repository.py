from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import Category, Product
from app.services.catalog_service import (
    search_key,
    validate_is_active,
    validate_new_product,
    validate_product_changes,
)


class ProductRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, product_id: int) -> Product | None:
        return self.session.get(Product, product_id)

    def list_public(
        self, category_id: int | None = None, search: str | None = None
    ) -> list[Product]:
        """El catálogo que ve el público: productos activos **de categorías
        activas**, en el orden del menú (categoría, luego posición del producto,
        luego id), con sus imágenes y su categoría ya cargadas.

        `search` busca en nombre y descripción sin distinguir mayúsculas ni
        acentos, y cada palabra tiene que aparecer (`"milanesa papas"` exige las
        dos). Se filtra en Python y no en SQL a propósito: SQLite no ignora
        acentos, y un catálogo de comida son decenas de productos. Si algún día
        fueran miles, este es el punto a mover a la base.
        """
        query = (
            select(Product)
            .join(Product.category)
            .where(Product.is_active.is_(True), Category.is_active.is_(True))
            .options(selectinload(Product.images), joinedload(Product.category))
            .order_by(Category.sort_order, Category.id, Product.sort_order, Product.id)
        )
        if category_id is not None:
            query = query.where(Product.category_id == category_id)
        products = list(self.session.scalars(query).unique())

        terms = search_key(search).split()
        if not terms:
            return products
        return [p for p in products if self._matches(p, terms)]

    def create(
        self,
        *,
        name: str,
        category_id: int,
        base_price: int,
        description: str | None = None,
        is_active: bool = True,
    ) -> Product:
        """Crea un producto validando **todas** las reglas de `T-3.2.1` (precio
        en centavos mayor que cero, categoría existente, nombre, descripción):
        ninguno llega a la base sin pasar por ellas. Va al final de su categoría."""
        data = validate_new_product(
            {
                "name": name,
                "category_id": category_id,
                "base_price": base_price,
                "description": description,
                "is_active": is_active,
            },
            self._category_ids(),
        )
        product = Product(
            name=data.name,
            category_id=data.category_id,
            base_price=data.base_price,
            description=data.description,
            is_active=data.is_active,
            sort_order=self._next_sort_order(data.category_id),
        )
        self.session.add(product)
        self.session.flush()
        return product

    def update(self, product: Product, **changes: object) -> Product:
        """Cambia solo los campos que se pasan (semántica de PATCH), validados
        con las reglas de edición de `T-3.2.1`. Si algo no es válido no se
        cambia nada."""
        for field, value in validate_product_changes(changes, self._category_ids()).items():
            setattr(product, field, value)
        self.session.flush()
        return product

    def set_active(self, product: Product, is_active: bool) -> Product:
        """Activa o desactiva (la "baja lógica": un producto con pedidos no se
        borra, se oculta)."""
        product.is_active = validate_is_active(is_active)
        self.session.flush()
        return product

    @staticmethod
    def _matches(product: Product, terms: list[str]) -> bool:
        haystack = search_key(f"{product.name} {product.description or ''}")
        return all(term in haystack for term in terms)

    def _category_ids(self) -> set[int]:
        return set(self.session.scalars(select(Category.id)))

    def _next_sort_order(self, category_id: int) -> int:
        highest = self.session.scalar(
            select(func.max(Product.sort_order)).where(Product.category_id == category_id)
        )
        return 0 if highest is None else highest + 1
