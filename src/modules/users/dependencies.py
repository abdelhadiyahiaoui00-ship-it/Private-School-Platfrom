from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import DBSessionDep
from src.modules.users.service import UserService


def get_user_service(session: DBSessionDep) -> UserService:
    return UserService(session)
