from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token
from app.db.session import get_session
from app.models import User
from app.schemas.auth import LoginIn, RegisterIn, TokenOut
from app.schemas.user import UserOut
from app.services.auth_service import AuthService

REFRESH_COOKIE_NAME = "mc_refresh"

SessionDep = Annotated[Session, Depends(get_session)]

router = APIRouter(prefix="/auth", tags=["auth"])


def refresh_cookie_path() -> str:
    """Path acotado: la cookie solo se manda a los endpoints de auth (§16.1)."""
    return f"{settings.api_prefix}/auth"


def set_refresh_cookie(response: Response, user: User) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=create_refresh_token(user),
        httponly=True,
        # En producción el front está en Vercel y la API en el VPS: es cross-site
        # real, así que la cookie necesita SameSite=None, que a su vez exige
        # Secure (§17). En desarrollo es http://localhost, donde Secure la
        # bloquearía.
        secure=settings.app_env == "production",
        samesite=settings.cookie_samesite,
        path=refresh_cookie_path(),
        max_age=settings.refresh_token_days * 24 * 60 * 60,
    )


def session_response(user: User) -> TokenOut:
    return TokenOut(
        access_token=create_access_token(user),
        expires_in=settings.access_token_minutes * 60,
        user=UserOut.model_validate(user),
    )


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(data: RegisterIn, response: Response, session: SessionDep) -> TokenOut:
    """Alta de cliente con login automático: devuelve el access token y deja la
    cookie de refresh, igual que el login."""
    user = AuthService(session).register(
        first_name=data.first_name,
        last_name=data.last_name,
        email=data.email,
        password=data.password,
        phone=data.phone,
    )
    set_refresh_cookie(response, user)
    return session_response(user)


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, response: Response, session: SessionDep) -> TokenOut:
    user = AuthService(session).authenticate(email=data.email, password=data.password)
    set_refresh_cookie(response, user)
    return session_response(user)
