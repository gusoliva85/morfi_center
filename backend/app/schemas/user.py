from pydantic import BaseModel, ConfigDict

from app.core.enums import Role


class UserOut(BaseModel):
    """Usuario tal como lo ve el cliente de la API: sin `password_hash` ni
    ningún otro dato sensible."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    first_name: str
    last_name: str
    email: str
    phone: str | None
    role: Role
