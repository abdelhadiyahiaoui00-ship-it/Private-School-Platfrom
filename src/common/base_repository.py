from typing import Any, Generic, Type, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.interfaces.repository_interface import IRepository

T = TypeVar("T")


class BaseRepository(IRepository[T], Generic[T]):
    model: Type[T]

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: int) -> T | None:
        return await self._session.get(self.model, id)

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[T]:
        result = await self._session.execute(
            select(self.model).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, obj: T) -> T:
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def update(self, obj: T) -> T:
        merged = await self._session.merge(obj)
        await self._session.flush()
        await self._session.refresh(merged)
        return merged

    async def delete(self, id: int) -> None:
        obj = await self.get_by_id(id)
        if obj:
            await self._session.delete(obj)
            await self._session.flush()

    async def exists(self, id: int) -> bool:
        result = await self._session.execute(
            select(func.count()).select_from(self.model).where(self.model.id == id)
        )
        return result.scalar_one() > 0

    async def get_by_field(self, field: str, value: Any) -> T | None:
        column = getattr(self.model, field)
        result = await self._session.execute(
            select(self.model).where(column == value)
        )
        return result.scalar_one_or_none()

    async def get_many_by_field(self, field: str, value: Any, skip: int = 0, limit: int = 100) -> list[T]:
        column = getattr(self.model, field)
        result = await self._session.execute(
            select(self.model).where(column == value).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def count(self) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(self.model)
        )
        return result.scalar_one()

    async def count_by_field(self, field: str, value: Any) -> int:
        column = getattr(self.model, field)
        result = await self._session.execute(
            select(func.count()).select_from(self.model).where(column == value)
        )
        return result.scalar_one()
