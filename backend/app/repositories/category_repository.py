from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ConflictError
from app.models import Category
from app.services.catalog_service import (
    build_category_slug,
    compute_reorder,
    validate_category_name,
)

SLUG_RACE = "Se creó otra categoría al mismo tiempo. Probá de nuevo."

# Siempre en el orden del menú; el id desempata para que sea determinista.
_MENU_ORDER = (Category.sort_order, Category.id)


class CategoryRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, category_id: int) -> Category | None:
        return self.session.get(Category, category_id)

    def get_by_slug(self, slug: str) -> Category | None:
        return self.session.scalar(select(Category).where(Category.slug == slug))

    def list_all(self) -> list[Category]:
        """Todas, en el orden del menú (lo que ve el admin)."""
        return list(self.session.scalars(select(Category).order_by(*_MENU_ORDER)))

    def list_active(self) -> list[Category]:
        """Solo las activas, en el orden del menú (lo que ve el público)."""
        query = select(Category).where(Category.is_active.is_(True)).order_by(*_MENU_ORDER)
        return list(self.session.scalars(query))

    def create(self, name: str, *, is_active: bool = True) -> Category:
        """Crea una categoría al final del menú.

        Valida el nombre y calcula el slug acá (no en quien llama): así ninguna
        categoría puede llegar a la base sin pasar por las reglas. Dos altas
        simultáneas pueden calcular el mismo slug libre; la base frena a la
        segunda (`UNIQUE`) y eso sale como 409 —no un 500— con `rollback`,
        igual que el registro de usuarios.
        """
        clean_name = validate_category_name(name)
        category = Category(
            name=clean_name,
            slug=build_category_slug(clean_name, self._taken_slugs()),
            sort_order=self._next_sort_order(),
            is_active=is_active,
        )
        try:
            self.session.add(category)
            self.session.flush()
        except IntegrityError as exc:
            self.session.rollback()
            raise ConflictError(SLUG_RACE) from exc
        return category

    def update(
        self, category: Category, *, name: str | None = None, is_active: bool | None = None
    ) -> Category:
        """Cambia solo lo que se pasa (`None` = no tocar; ninguno de los dos
        campos admite `None` como valor). **No cambia el slug** al renombrar:
        los links que ya apunten a la categoría no se rompen."""
        if name is not None:
            category.name = validate_category_name(name)
        if is_active is not None:
            category.is_active = is_active
        self.session.flush()
        return category

    def reorder(self, ordered_ids: Sequence[int]) -> list[Category]:
        """Reordena el menú con la lista **completa** de ids en el orden deseado
        (ver `compute_reorder`). Si la lista es inválida no se cambia nada."""
        categories = {category.id: category for category in self.list_all()}
        positions = compute_reorder(categories.keys(), ordered_ids)
        for category_id, position in positions.items():
            categories[category_id].sort_order = position
        self.session.flush()
        return self.list_all()

    def _taken_slugs(self) -> set[str]:
        return set(self.session.scalars(select(Category.slug)))

    def _next_sort_order(self) -> int:
        highest = self.session.scalar(select(func.max(Category.sort_order)))
        return 0 if highest is None else highest + 1
