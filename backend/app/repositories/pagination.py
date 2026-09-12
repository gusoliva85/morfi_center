"""Página de resultados genérica, compartida por todos los repositorios.

Coincide con el formato de paginación de la API (§11 de
``documentacion/02_Documento_Tecnico.md``): ``{items, page, page_size, total}``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


def clamp_pagination(page: int | None, page_size: int | None) -> tuple[int, int]:
    """Normaliza page/page_size a valores válidos (page >= 1, 1 <= page_size <= 100)."""
    safe_page = max(1, page or 1)
    safe_size = min(MAX_PAGE_SIZE, max(1, page_size or DEFAULT_PAGE_SIZE))
    return safe_page, safe_size


@dataclass(frozen=True)
class Page(Generic[T]):
    items: list[T]
    page: int
    page_size: int
    total: int

    @property
    def pages(self) -> int:
        if self.page_size <= 0:
            return 0
        return -(-self.total // self.page_size)  # ceil sin importar math


__all__ = ["Page", "clamp_pagination", "DEFAULT_PAGE_SIZE", "MAX_PAGE_SIZE"]
