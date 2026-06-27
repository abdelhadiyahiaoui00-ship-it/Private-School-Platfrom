import re
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.pagination import build_pagination
from src.modules.audit.service import log_action
from src.modules.branches.exceptions import (
    BranchHasActiveDependencies,
    BranchNameTaken,
    BranchNotFound,
    InvalidMapUrl,
    TooManyPhotos,
)
from src.modules.branches.models import Branch
from src.modules.branches.repository import BranchRepository
from src.modules.branches.schemas import BranchResponse
from src.modules.users.models import User

GOOGLE_MAPS_EMBED_PATTERN = re.compile(
    r"^https://www\.google\.com/maps/embed(\?|/)"
)


def _validate_map_url(url: Optional[str]) -> None:
    if url and not GOOGLE_MAPS_EMBED_PATTERN.match(url):
        raise InvalidMapUrl()


def _build_branch_response(branch: Branch, total_users: int = 0) -> BranchResponse:
    return BranchResponse(
        id=branch.id,
        name=branch.name,
        address=branch.address,
        phone=branch.phone,
        email=branch.email,
        latitude=float(branch.latitude) if branch.latitude is not None else None,
        longitude=float(branch.longitude) if branch.longitude is not None else None,
        map_embed_url=branch.map_embed_url,
        photo_urls=branch.photo_urls or [],
        description=branch.description,
        is_active=branch.is_active,
        created_at=branch.created_at,
        updated_at=branch.updated_at,
        active_classes_count=0,   # Sprint 4 will populate from classes table
        total_users_count=total_users,
    )


class BranchService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = BranchRepository(session)

    async def list_branches(
        self,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        branches, total = await self._repo.get_all(
            search=search, is_active=is_active, page=page, page_size=page_size
        )
        stats = await self._repo.get_stats()
        pagination = build_pagination(page, page_size, total)
        items = []
        for b in branches:
            users_count = await self._repo.get_total_users_count(b.id)
            items.append(_build_branch_response(b, users_count))
        return {"items": items, "pagination": pagination, "stats": stats}

    async def get_my_branches(self, actor: User) -> list:
        if actor.role in ("owner", "superAdmin"):
            branches = await self._repo.get_all_for_owner()
        else:
            branches = await self._repo.get_assigned_for_admin(actor.id)
        return branches

    async def get_branch(self, branch_id: int) -> BranchResponse:
        branch = await self._repo.get_by_id(branch_id)
        if not branch:
            raise BranchNotFound()
        users_count = await self._repo.get_total_users_count(branch_id)
        return _build_branch_response(branch, users_count)

    async def create_branch(self, data: dict, actor: User, ip: Optional[str] = None) -> BranchResponse:
        name = data["name"].strip()
        if await self._repo.name_exists(name):
            raise BranchNameTaken()

        photo_urls = data.get("photo_urls") or []
        if len(photo_urls) > 10:
            raise TooManyPhotos()

        map_embed_url = data.get("map_embed_url") or None
        _validate_map_url(map_embed_url)

        branch = Branch(
            name=name,
            address=data.get("address") or None,
            phone=data.get("phone") or None,
            email=data.get("email") or None,
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            map_embed_url=map_embed_url,
            photo_urls=photo_urls,
            description=data.get("description") or None,
            is_active=data.get("is_active", True),
        )
        branch = await self._repo.create(branch)

        await log_action(
            self._session,
            user_id=actor.id,
            action="BRANCH_CREATED",
            category="branches",
            entity_type="branch",
            entity_id=branch.id,
            metadata={"name": branch.name, "address": branch.address},
            ip_address=ip,
        )

        return _build_branch_response(branch)

    async def update_branch(self, branch_id: int, data: dict, actor: User, ip: Optional[str] = None) -> BranchResponse:
        branch = await self._repo.get_by_id(branch_id)
        if not branch:
            raise BranchNotFound()

        changed = []

        if "name" in data and data["name"] is not None:
            new_name = data["name"].strip()
            if new_name != branch.name:
                if await self._repo.name_exists(new_name, exclude_id=branch_id):
                    raise BranchNameTaken()
                branch.name = new_name
                changed.append("name")

        for field in ("address", "phone", "email", "description", "is_active"):
            if field in data and data[field] is not None:
                setattr(branch, field, data[field])
                changed.append(field)

        for field in ("latitude", "longitude"):
            if field in data:
                setattr(branch, field, data[field])
                changed.append(field)

        if "map_embed_url" in data:
            url = data["map_embed_url"] or None
            _validate_map_url(url)
            branch.map_embed_url = url
            changed.append("mapEmbedUrl")

        if "photo_urls" in data and data["photo_urls"] is not None:
            if len(data["photo_urls"]) > 10:
                raise TooManyPhotos()
            branch.photo_urls = data["photo_urls"]
            changed.append("photoUrls")

        branch = await self._repo.save(branch)

        await log_action(
            self._session,
            user_id=actor.id,
            action="BRANCH_UPDATED",
            category="branches",
            entity_type="branch",
            entity_id=branch_id,
            metadata={"changedFields": changed},
            ip_address=ip,
        )

        users_count = await self._repo.get_total_users_count(branch_id)
        return _build_branch_response(branch, users_count)

    async def set_status(self, branch_id: int, is_active: bool, actor: User, ip: Optional[str] = None) -> dict:
        branch = await self._repo.get_by_id(branch_id)
        if not branch:
            raise BranchNotFound()

        # Sprint 4 will add real class check — for now 0 active classes always
        # active_classes = await self._class_repo.count_active_for_branch(branch_id)
        # if not is_active and active_classes > 0:
        #     raise BranchHasActiveDependencies()

        branch.is_active = is_active
        await self._repo.save(branch)

        await log_action(
            self._session,
            user_id=actor.id,
            action="BRANCH_UPDATED",
            category="branches",
            entity_type="branch",
            entity_id=branch_id,
            metadata={"isActive": is_active},
            ip_address=ip,
        )

        return {"id": branch_id, "isActive": is_active}

    async def delete_branch(self, branch_id: int, actor: User, ip: Optional[str] = None) -> None:
        branch = await self._repo.get_by_id(branch_id)
        if not branch:
            raise BranchNotFound()

        # Sprint 4 will add real class check — for now allow deletion
        # classes_count = await self._class_repo.count_for_branch(branch_id)
        # if classes_count > 0:
        #     raise BranchHasActiveDependencies()

        await log_action(
            self._session,
            user_id=actor.id,
            action="BRANCH_DELETED",
            category="branches",
            entity_type="branch",
            entity_id=branch_id,
            metadata={"name": branch.name},
            ip_address=ip,
        )

        await self._repo.delete(branch)
