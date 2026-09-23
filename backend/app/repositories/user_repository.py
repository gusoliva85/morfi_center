from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import AuthProvider, Role, UserStatus
from app.models import User, UserAuthProvider
from app.services.user_service import normalize_email


class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, user_id: int) -> User | None:
        return self.session.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        # Normaliza acá también (no solo en el servicio): el email se guarda
        # siempre en minúsculas, así que buscar sin normalizar no encontraría
        # "Ana@Example.com" y habilitaría cuentas duplicadas por mayúsculas.
        return self.session.scalar(select(User).where(User.email == normalize_email(email)))

    def create(
        self,
        *,
        first_name: str,
        last_name: str,
        email: str,
        password_hash: str | None = None,
        phone: str | None = None,
        role: Role = Role.CUSTOMER,
        status: UserStatus = UserStatus.ACTIVE,
    ) -> User:
        user = User(
            first_name=first_name,
            last_name=last_name,
            email=normalize_email(email),
            password_hash=password_hash,
            phone=phone,
            role=role,
            status=status,
        )
        self.session.add(user)
        self.session.flush()  # asigna el id sin cerrar la transacción
        return user

    def list(
        self, role: Role | None = None, page: int = 1, page_size: int = 20
    ) -> tuple[list[User], int]:
        """Devuelve (usuarios de la página, total sin paginar) — el total lo
        necesita la respuesta paginada de la API (§21 del Documento Técnico)."""
        filters = [User.role == role] if role is not None else []

        total = self.session.scalar(select(func.count()).select_from(User).where(*filters)) or 0
        rows = self.session.scalars(
            select(User)
            .where(*filters)
            .order_by(User.id)
            .offset((max(page, 1) - 1) * page_size)
            .limit(page_size)
        ).all()
        return list(rows), total

    def get_provider(self, provider: AuthProvider, uid: str) -> UserAuthProvider | None:
        return self.session.scalar(
            select(UserAuthProvider).where(
                UserAuthProvider.provider == provider,
                UserAuthProvider.provider_uid == uid,
            )
        )

    def link_provider(
        self, user: User, provider: AuthProvider, provider_uid: str | None = None
    ) -> UserAuthProvider:
        link = UserAuthProvider(user_id=user.id, provider=provider, provider_uid=provider_uid)
        self.session.add(link)
        self.session.flush()
        return link
