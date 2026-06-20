from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import DBSessionDep
from src.core.jwt import decode_access_token
from src.modules.auth.exceptions import TokenInvalid, TokenExpired
from src.modules.auth.service import AuthService
from src.modules.users.models import User
from src.modules.users.repository import UserRepository

security = HTTPBearer()


def get_auth_service(session: DBSessionDep) -> AuthService:
    return AuthService(session)


async def get_current_user(
    token: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    session: DBSessionDep,
) -> User:
    try:
        payload = decode_access_token(token.credentials)
    except Exception as e:
        # Wrap underlying jwt errors into our app exceptions
        if type(e).__name__ == "TokenExpired":
            raise TokenExpired()
        raise TokenInvalid()

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise TokenInvalid()

    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(int(user_id_str))

    if not user:
        raise TokenInvalid(message="User not found.")

    if user.status != "active":
        from src.modules.auth.exceptions import AccountInactive
        raise AccountInactive()

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


# ─── Role guards ──────────────────────────────────────────────────────────────

def require_role(roles: list[str]):
    def role_checker(user: CurrentUser) -> User:
        if user.role not in roles:
            from src.core.exceptions import PermissionDenied
            raise PermissionDenied(message=f"Requires one of roles: {', '.join(roles)}")
        return user
    return Depends(role_checker)


def require_manage_users(user: CurrentUser = Depends(require_role(["owner", "superAdmin", "admin"]))) -> User:
    """Owner & superAdmin always pass. Admin needs manage_users flag."""
    if user.role in ("owner", "superAdmin"):
        return user
    
    if user.role == "admin":
        perms = user.permissions or {}
        if perms.get("manageUsers") or perms.get("manage_users"):
            return user

    from src.core.exceptions import PermissionDenied
    raise PermissionDenied(message="Requires manage users permission.")
