from collections.abc import Mapping
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models import Product, User
from app.repositories.product_repository import ProductRepository
from app.services.audit import record_audit

PRODUCT_NOT_FOUND = "No existe ese producto."

_AUDITED_FIELDS = ("name", "category_id", "base_price", "description", "is_active")


def _snapshot(product: Product) -> dict[str, Any]:
    return {field: getattr(product, field) for field in _AUDITED_FIELDS}


class CatalogAdminService:
    """Lo que un admin hace sobre el catálogo, dejando rastro en `audit_log`.

    Se audita todo lo que toca un producto (sobre todo el **precio**, que es
    plata: si un cliente discute un monto, hay que poder ver quién lo cambió y
    cuándo). Igual que en los demás paneles, lo que no cambia nada no deja
    rastro. Las reglas de validación viven en el repositorio y en
    `catalog_service`; este servicio no las repite.
    """

    def __init__(self, session: Session) -> None:
        self.session = session
        self.products = ProductRepository(session)

    def get_product(self, product_id: int) -> Product:
        product = self.products.get(product_id)
        if product is None:
            raise NotFoundError(PRODUCT_NOT_FOUND)
        return product

    def create_product(
        self, actor: User, fields: Mapping[str, Any], *, ip: str | None = None
    ) -> Product:
        product = self.products.create(**fields)
        record_audit(
            self.session,
            actor=actor,
            action="product.create",
            entity_type="product",
            entity_id=product.id,
            after=_snapshot(product),
            ip=ip,
        )
        self.session.flush()
        return product

    def update_product(
        self, product_id: int, changes: Mapping[str, Any], actor: User, *, ip: str | None = None
    ) -> Product:
        """Edita solo lo que venga en `changes`. Auditoría con **solo los campos
        que de verdad cambiaron** (mandar el mismo precio no cuenta)."""
        product = self.get_product(product_id)
        before = _snapshot(product)

        self.products.update(product, **changes)  # valida; si falla, no cambia nada

        after = _snapshot(product)
        changed = [field for field in _AUDITED_FIELDS if before[field] != after[field]]
        if changed:
            record_audit(
                self.session,
                actor=actor,
                action="product.update",
                entity_type="product",
                entity_id=product.id,
                before={field: before[field] for field in changed},
                after={field: after[field] for field in changed},
                ip=ip,
            )
            self.session.flush()
        return product

    def deactivate_product(self, product_id: int, actor: User, *, ip: str | None = None) -> None:
        """Baja lógica: el producto se oculta, no se borra (puede tener pedidos).
        Es idempotente: dar de baja uno que ya estaba inactivo no hace nada ni
        deja rastro. Para volver a mostrarlo: `update_product(is_active=True)`."""
        product = self.get_product(product_id)
        if not product.is_active:
            return

        self.products.set_active(product, False)
        record_audit(
            self.session,
            actor=actor,
            action="product.deactivate",
            entity_type="product",
            entity_id=product.id,
            before={"is_active": True},
            after={"is_active": False},
            ip=ip,
        )
        self.session.flush()
