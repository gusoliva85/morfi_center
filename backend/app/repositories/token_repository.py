"""Acceso a datos de tokens revocados (ver `app/models/token.py`)."""

from __future__ import annotations

import datetime as dt

from sqlalchemy.orm import Session

from app.models.token import RevokedToken


class TokenRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def is_revoked(self, jti: str) -> bool:
        return self.session.get(RevokedToken, jti) is not None

    def revoke(self, jti: str, expires_at: dt.datetime) -> None:
        """Marca `jti` como revocado. Idempotente: revocar dos veces no falla."""
        if self.is_revoked(jti):
            return
        self.session.add(RevokedToken(jti=jti, expires_at=expires_at))
        self.session.flush()


__all__ = ["TokenRepository"]
