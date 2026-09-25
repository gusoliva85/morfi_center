from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import NOT_ALLOWED, AdminUser, BearerDep, SessionDep, get_current_user
from app.core.enums import Role
from app.core.errors import ForbiddenError, NotFoundError
from app.repositories.category_repository import CategoryRepository
from app.schemas.catalog import (
    CategoryCreateIn,
    CategoryOut,
    CategoryReorderIn,
    CategoryUpdateIn,
)

router = APIRouter(prefix="/catalog", tags=["catalog"])

CATEGORY_NOT_FOUND = "No existe esa categoría."


def _categories(categories) -> list[CategoryOut]:
    return [CategoryOut.model_validate(c) for c in categories]


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(
    session: SessionDep,
    credentials: BearerDep,
    include_inactive: Annotated[bool, Query(alias="all")] = False,
) -> list[CategoryOut]:
    """Categorías en el orden del menú. Público: solo las activas. Con
    `?all=true` (solo admin) también las inactivas, para gestionarlas.

    La sesión se pide únicamente cuando se pide `all=true`: el listado normal
    no exige (ni mira) ningún token.
    """
    repo = CategoryRepository(session)
    if not include_inactive:
        return _categories(repo.list_active())

    user = get_current_user(session, credentials)  # 401 sin sesión
    if user.role != Role.ADMIN:
        raise ForbiddenError(NOT_ALLOWED)
    return _categories(repo.list_all())


@router.post("/categories", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(data: CategoryCreateIn, admin: AdminUser, session: SessionDep) -> CategoryOut:
    """Alta de categoría al final del menú; el slug sale del nombre."""
    category = CategoryRepository(session).create(data.name, is_active=data.is_active)
    return CategoryOut.model_validate(category)


# `/categories/reorder` se declara antes que `/categories/{category_id}`: son
# métodos distintos (POST vs PATCH) y no chocan, pero así el orden de lectura
# coincide con lo que el router evalúa.
@router.post("/categories/reorder", response_model=list[CategoryOut])
def reorder_categories(
    data: CategoryReorderIn, admin: AdminUser, session: SessionDep
) -> list[CategoryOut]:
    """Reordena el menú con la lista completa de ids en el orden deseado y
    devuelve todas las categorías ya ordenadas."""
    return _categories(CategoryRepository(session).reorder(data.ids))


@router.patch("/categories/{category_id}", response_model=CategoryOut)
def update_category(
    category_id: int, data: CategoryUpdateIn, admin: AdminUser, session: SessionDep
) -> CategoryOut:
    """Renombra y/o activa/desactiva una categoría. El slug no cambia."""
    repo = CategoryRepository(session)
    category = repo.get(category_id)
    if category is None:
        raise NotFoundError(CATEGORY_NOT_FOUND)
    repo.update(category, **data.model_dump(exclude_unset=True))
    return CategoryOut.model_validate(category)
