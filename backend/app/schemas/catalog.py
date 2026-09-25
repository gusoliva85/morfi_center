from pydantic import BaseModel, ConfigDict, model_validator


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    sort_order: int
    is_active: bool


class CategoryCreateIn(BaseModel):
    """`name` se valida en el repositorio (con las reglas del catálogo y sus
    mensajes), por eso acá es un texto cualquiera."""

    model_config = ConfigDict(extra="forbid")

    name: str
    is_active: bool = True


class CategoryUpdateIn(BaseModel):
    """PATCH: solo se cambia lo que venga. Un campo enviado como `null` es un
    error (ninguno de los dos admite vacío), no un "no tocar"."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def _sent_fields_cannot_be_null(self) -> "CategoryUpdateIn":
        for field in self.model_fields_set:
            if getattr(self, field) is None:
                raise ValueError(f"«{field}» no puede ser nulo.")
        return self


class CategoryReorderIn(BaseModel):
    """La lista completa de ids de categorías, en el orden deseado."""

    model_config = ConfigDict(extra="forbid")

    ids: list[int]
