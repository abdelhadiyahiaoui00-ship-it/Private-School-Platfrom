from sqlalchemy.ext.asyncio import AsyncSession

from src.common.interfaces.service_interface import IService
from src.common.base_repository import BaseRepository
from src.core.exceptions import ResourceNotFound, HistoricalUserCannotWrite


class BaseService(IService):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _get_or_404(self, repo: BaseRepository, id: int, label: str = "Resource"):
        obj = await repo.get_by_id(id)
        if obj is None:
            raise ResourceNotFound(message=f"{label} not found.")
        return obj

    def _check_historical(self, user) -> None:
        if getattr(user, "is_historical", False):
            raise HistoricalUserCannotWrite()
