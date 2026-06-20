"""
Auth service — Sprint 1.
Handles login, refresh, password reset, and auth token generation.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.common.email import send_email
from src.core.config import settings
from src.core.security import (
    create_access_token,
    generate_raw_token,
    generate_reset_token,
    hash_password,
    hash_token,
    verify_password,
)
from src.modules.audit.service import log_action
from src.modules.auth.exceptions import (
    AccountInactive,
    InvalidCredentials,
    InvalidRefreshToken,
    TokenExpired,
    TokenInvalid,
    WrongCurrentPassword,
)
from src.modules.auth.models import PasswordResetToken, SessionAuth
from src.modules.auth.repository import AuthRepository
from src.modules.users.repository import UserRepository


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = AuthRepository(session)
        self._user_repo = UserRepository(session)

    async def login(self, identifier: str, password: str, ip: Optional[str] = None, user_agent: Optional[str] = None) -> dict:
        user = await self._user_repo.get_by_identifier(identifier)
        if not user or not verify_password(password, user.password_hash):
            raise InvalidCredentials()

        if user.status != "active":
            raise AccountInactive()

        # Update last login
        user.last_login = datetime.now(timezone.utc)
        await self._user_repo.save(user)

        # Create refresh session
        raw_refresh = generate_raw_token()
        refresh_hash = hash_token(raw_refresh)
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        session_auth = SessionAuth(
            user_id=user.id,
            refresh_token_hash=refresh_hash,
            expires_at=expires_at,
            device_info=user_agent[:255] if user_agent else None,
            ip_address=ip,
        )
        await self._repo.create_session(session_auth)

        # Create access token
        access_token = create_access_token(data={"sub": str(user.id)})

        await log_action(
            self._session,
            user_id=user.id,
            action="LOGIN_SUCCESS",
            category="auth",
            ip_address=ip,
        )

        return {
            "tokens": {"access_token": access_token, "refresh_token": raw_refresh},
            "user": user,
        }

    async def refresh_token(self, refresh_token: str, ip: Optional[str] = None) -> dict:
        token_hash = hash_token(refresh_token)
        session_auth = await self._repo.get_session_by_hash(token_hash)

        if not session_auth or session_auth.revoked_at:
            raise InvalidRefreshToken()

        if session_auth.expires_at < datetime.now(timezone.utc):
            raise InvalidRefreshToken(message="Refresh token has expired.")

        user = session_auth.user
        if not user or user.status != "active":
            raise AccountInactive()

        # Issue new access token
        access_token = create_access_token(data={"sub": str(user.id)})

        # Issue new refresh token (token rotation)
        new_raw_refresh = generate_raw_token()
        new_refresh_hash = hash_token(new_raw_refresh)
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        new_session = SessionAuth(
            user_id=user.id,
            refresh_token_hash=new_refresh_hash,
            expires_at=expires_at,
            device_info=session_auth.device_info,
            ip_address=ip,
        )
        await self._repo.create_session(new_session)

        # Revoke old session
        await self._repo.revoke_session(session_auth.id, datetime.now(timezone.utc))

        return {
            "tokens": {"access_token": access_token, "refresh_token": new_raw_refresh},
            "user": user,
        }

    async def logout(self, refresh_token: str, ip: Optional[str] = None) -> None:
        token_hash = hash_token(refresh_token)
        session_auth = await self._repo.get_session_by_hash(token_hash)
        if session_auth and not session_auth.revoked_at:
            await self._repo.revoke_session(session_auth.id, datetime.now(timezone.utc))
            await log_action(
                self._session,
                user_id=session_auth.user_id,
                action="LOGOUT",
                category="auth",
                ip_address=ip,
            )

    async def change_password(
        self, user_id: int, current_password: str, new_password: str, ip: Optional[str] = None
    ) -> None:
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise AccountInactive()

        if not verify_password(current_password, user.password_hash):
            raise WrongCurrentPassword()

        user.password_hash = hash_password(new_password)
        user.must_change_password = False
        await self._user_repo.save(user)

        # Revoke all existing sessions
        from src.modules.users.service import _revoke_all_sessions
        await _revoke_all_sessions(self._session, user_id)

        await log_action(
            self._session,
            user_id=user_id,
            action="PASSWORD_CHANGED",
            category="auth",
            ip_address=ip,
        )

    async def forgot_password(self, email: str, ip: Optional[str] = None) -> None:
        user = await self._user_repo.get_by_email(email)
        if not user or user.status != "active":
            return  # Silently ignore to prevent email enumeration

        raw_token = generate_reset_token()
        token_hash = hash_token(raw_token)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.PASSWORD_RESET_EXPIRE_HOURS)

        reset_token = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        await self._repo.create_reset_token(reset_token)

        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={raw_token}"

        await log_action(
            self._session,
            user_id=user.id,
            action="PASSWORD_RESET_REQUESTED",
            category="auth",
            ip_address=ip,
        )

        from asyncio import ensure_future
        ensure_future(
            send_email(
                "password_reset",
                user.email,
                firstName=user.first_name,
                resetLink=reset_link,
            )
        )

    async def reset_password(self, token: str, new_password: str, ip: Optional[str] = None) -> None:
        token_hash = hash_token(token)
        reset_entry = await self._repo.get_reset_token(token_hash)

        if not reset_entry or reset_entry.used_at:
            raise TokenInvalid()

        if reset_entry.expires_at < datetime.now(timezone.utc):
            raise TokenExpired()

        user = reset_entry.user
        if not user or user.status != "active":
            raise AccountInactive()

        user.password_hash = hash_password(new_password)
        user.must_change_password = False
        await self._user_repo.save(user)

        await self._repo.mark_reset_token_used(reset_entry.id, datetime.now(timezone.utc))

        # Revoke all sessions
        from src.modules.users.service import _revoke_all_sessions
        await _revoke_all_sessions(self._session, user.id)

        await log_action(
            self._session,
            user_id=user.id,
            action="PASSWORD_RESET_COMPLETED",
            category="auth",
            ip_address=ip,
        )
