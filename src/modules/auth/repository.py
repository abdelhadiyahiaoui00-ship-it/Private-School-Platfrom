from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.auth.models import PasswordResetToken, SessionAuth


class AuthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_session(self, session_auth: SessionAuth) -> SessionAuth:
        self._session.add(session_auth)
        await self._session.flush()
        await self._session.refresh(session_auth)
        return session_auth

    async def get_session_by_hash(self, token_hash: str) -> Optional[SessionAuth]:
        result = await self._session.execute(
            select(SessionAuth)
            .where(SessionAuth.refresh_token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def revoke_session(self, session_id: int, revoked_at) -> None:
        await self._session.execute(
            update(SessionAuth)
            .where(SessionAuth.id == session_id)
            .values(revoked_at=revoked_at)
        )
        await self._session.flush()

    async def create_reset_token(self, reset_token: PasswordResetToken) -> PasswordResetToken:
        self._session.add(reset_token)
        await self._session.flush()
        await self._session.refresh(reset_token)
        return reset_token

    async def get_reset_token(self, token_hash: str) -> Optional[PasswordResetToken]:
        result = await self._session.execute(
            select(PasswordResetToken)
            .where(PasswordResetToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def mark_reset_token_used(self, token_id: int, used_at) -> None:
        await self._session.execute(
            update(PasswordResetToken)
            .where(PasswordResetToken.id == token_id)
            .values(used_at=used_at)
        )
        await self._session.flush()
