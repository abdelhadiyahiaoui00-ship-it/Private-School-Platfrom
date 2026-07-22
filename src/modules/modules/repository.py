from typing import Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.modules.models import Module


class ModuleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, module_id: int) -> Optional[Module]:
        result = await self._session.execute(
            select(Module).where(Module.id == module_id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        search: Optional[str] = None,
        category: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Module], int]:
        q = select(Module)
        if search:
            q = q.where(Module.name.ilike(f"%{search}%"))
        if category:
            q = q.where(Module.category == category)
        if is_active is not None:
            q = q.where(Module.is_active == is_active)

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self._session.execute(count_q)).scalar_one()

        q = q.order_by(Module.name.asc()).offset((page - 1) * page_size).limit(page_size)
        result = await self._session.execute(q)
        return list(result.scalars().all()), total

    async def get_distinct_categories(self) -> list[str]:
        result = await self._session.execute(
            select(Module.category)
            .where(Module.category.isnot(None))
            .distinct()
            .order_by(Module.category)
        )
        return [row[0] for row in result.all()]

    async def name_exists(self, name: str, exclude_id: Optional[int] = None) -> bool:
        q = select(func.count()).select_from(Module).where(
            func.lower(Module.name) == name.lower()
        )
        if exclude_id:
            q = q.where(Module.id != exclude_id)
        result = await self._session.execute(q)
        return result.scalar_one() > 0

    async def get_classes_count(self, module_id: int) -> int:
        from src.modules.classes.models import Class
        result = await self._session.execute(
            select(func.count()).select_from(Class).where(Class.module_id == module_id)
        )
        return result.scalar_one()

    async def get_stats(self) -> dict:
        result = await self._session.execute(
            select(Module.is_active, func.count(Module.id)).group_by(Module.is_active)
        )
        rows = result.all()
        total = active = inactive = 0
        for is_active_val, cnt in rows:
            total += cnt
            if is_active_val:
                active += cnt
            else:
                inactive += cnt
        return {"total": total, "active": active, "inactive": inactive}

    async def create(self, module: Module) -> Module:
        self._session.add(module)
        await self._session.flush()
        await self._session.refresh(module)
        return module

    async def save(self, module: Module) -> Module:
        merged = await self._session.merge(module)
        await self._session.flush()
        await self._session.refresh(merged)
        return merged

    async def delete(self, module: Module) -> None:
        await self._session.delete(module)
        await self._session.flush()
