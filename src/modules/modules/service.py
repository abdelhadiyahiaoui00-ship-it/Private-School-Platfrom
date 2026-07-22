from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.pagination import build_pagination
from src.modules.audit.service import log_action
from src.modules.modules.exceptions import (
    ModuleHasActiveDependencies, ModuleNameTaken, ModuleNotFound
)
from src.modules.modules.models import Module
from src.modules.modules.repository import ModuleRepository
from src.modules.modules.schemas import ModuleResponse
from src.modules.users.models import User


def _build_response(module: Module, classes_count: int = 0) -> ModuleResponse:
    return ModuleResponse(
        id=module.id,
        name=module.name,
        description=module.description,
        category=module.category,
        color=module.color,
        is_active=module.is_active,
        classes_count=classes_count,
        created_by=module.created_by,
        created_at=module.created_at,
        updated_at=module.updated_at,
    )


class ModuleService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ModuleRepository(session)

    async def list_modules(
        self,
        search: Optional[str] = None,
        category: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        modules, total = await self._repo.get_all(
            search=search, category=category, is_active=is_active,
            page=page, page_size=page_size,
        )
        stats = await self._repo.get_stats()
        items = []
        for m in modules:
            cnt = await self._repo.get_classes_count(m.id)
            items.append(_build_response(m, cnt).model_dump(by_alias=True))
        return {
            "items": items,
            "pagination": build_pagination(page, page_size, total),
            "stats": stats,
        }

    async def get_categories(self) -> list[str]:
        return await self._repo.get_distinct_categories()

    async def get_module(self, module_id: int) -> dict:
        module = await self._repo.get_by_id(module_id)
        if not module:
            raise ModuleNotFound()
        cnt = await self._repo.get_classes_count(module_id)
        return _build_response(module, cnt).model_dump(by_alias=True)

    async def create_module(self, data: dict, actor: User, ip: Optional[str] = None) -> dict:
        name = data["name"].strip()
        if await self._repo.name_exists(name):
            raise ModuleNameTaken()

        module = Module(
            name=name,
            description=data.get("description") or None,
            category=data.get("category") or None,
            color=data.get("color") or None,
            is_active=True,
            created_by=actor.id,
        )
        module = await self._repo.create(module)

        await log_action(
            self._session, user_id=actor.id, action="MODULE_CREATED",
            category="academic", entity_type="module", entity_id=module.id,
            metadata={"name": module.name, "category": module.category},
            ip_address=ip,
        )
        return _build_response(module, 0).model_dump(by_alias=True)

    async def update_module(self, module_id: int, data: dict, actor: User, ip: Optional[str] = None) -> dict:
        module = await self._repo.get_by_id(module_id)
        if not module:
            raise ModuleNotFound()

        changed = []
        if "name" in data and data["name"]:
            new_name = data["name"].strip()
            if new_name != module.name:
                if await self._repo.name_exists(new_name, exclude_id=module_id):
                    raise ModuleNameTaken()
                module.name = new_name
                changed.append("name")

        for field in ("description", "category", "color"):
            if field in data:
                setattr(module, field, data[field] or None)
                changed.append(field)

        module = await self._repo.save(module)
        await log_action(
            self._session, user_id=actor.id, action="MODULE_UPDATED",
            category="academic", entity_type="module", entity_id=module_id,
            metadata={"changedFields": changed}, ip_address=ip,
        )
        cnt = await self._repo.get_classes_count(module_id)
        return _build_response(module, cnt).model_dump(by_alias=True)

    async def set_status(self, module_id: int, is_active: bool, actor: User, ip: Optional[str] = None) -> dict:
        module = await self._repo.get_by_id(module_id)
        if not module:
            raise ModuleNotFound()
        module.is_active = is_active
        await self._repo.save(module)
        await log_action(
            self._session, user_id=actor.id, action="MODULE_UPDATED",
            category="academic", entity_type="module", entity_id=module_id,
            metadata={"changedFields": ["isActive"], "isActive": is_active},
            ip_address=ip,
        )
        cnt = await self._repo.get_classes_count(module_id)
        return _build_response(module, cnt).model_dump(by_alias=True)

    async def delete_module(self, module_id: int, actor: User, ip: Optional[str] = None) -> None:
        module = await self._repo.get_by_id(module_id)
        if not module:
            raise ModuleNotFound()
        cnt = await self._repo.get_classes_count(module_id)
        if cnt > 0:
            raise ModuleHasActiveDependencies()
        await log_action(
            self._session, user_id=actor.id, action="MODULE_DELETED",
            category="academic", entity_type="module", entity_id=module_id,
            metadata={"name": module.name}, ip_address=ip,
        )
        await self._repo.delete(module)
