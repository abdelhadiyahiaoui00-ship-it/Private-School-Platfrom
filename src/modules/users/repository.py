"""
Users repository — Sprint 1.
All queries go through SQLAlchemy async ORM; no raw string interpolation.
"""
from typing import Optional

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.users.models import ParentStudentLink, User, UserBranch


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ─── Basic lookups ────────────────────────────────────────────────────────

    async def get_by_id(self, user_id: int) -> Optional[User]:
        result = await self._session.execute(
            select(User)
            .where(User.id == user_id)
            .options(
                selectinload(User.branch_links).selectinload(UserBranch.branch),
                selectinload(User.linked_students),
                selectinload(User.linked_parents),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self._session.execute(
            select(User).where(func.lower(User.email) == email.lower())
            .options(
                selectinload(User.branch_links).selectinload(UserBranch.branch),
                selectinload(User.linked_students),
                selectinload(User.linked_parents),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_phone(self, phone: str) -> Optional[User]:
        result = await self._session.execute(
            select(User).where(User.phone == phone)
            .options(
                selectinload(User.branch_links).selectinload(UserBranch.branch),
                selectinload(User.linked_students),
                selectinload(User.linked_parents),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_identifier(self, identifier: str) -> Optional[User]:
        """Match email (case-insensitive) OR exact phone."""
        result = await self._session.execute(
            select(User).where(
                or_(
                    func.lower(User.email) == identifier.lower(),
                    User.phone == identifier,
                )
            )
            .options(
                selectinload(User.branch_links).selectinload(UserBranch.branch),
                selectinload(User.linked_students),
                selectinload(User.linked_parents),
            )
        )
        return result.scalar_one_or_none()

    async def email_exists(self, email: str, exclude_id: Optional[int] = None) -> bool:
        q = select(func.count()).select_from(User).where(
            func.lower(User.email) == email.lower()
        )
        if exclude_id:
            q = q.where(User.id != exclude_id)
        result = await self._session.execute(q)
        return result.scalar_one() > 0

    async def phone_exists(self, phone: str, exclude_id: Optional[int] = None) -> bool:
        q = select(func.count()).select_from(User).where(User.phone == phone)
        if exclude_id:
            q = q.where(User.id != exclude_id)
        result = await self._session.execute(q)
        return result.scalar_one() > 0

    # ─── List with filters ────────────────────────────────────────────────────

    async def list_users(
        self,
        *,
        role: Optional[str] = None,
        status: Optional[str] = None,
        branch_id: Optional[int] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        branch_ids_scope: Optional[list[int]] = None,  # admin scope
    ) -> tuple[list[User], int]:
        q = select(User).options(
            selectinload(User.branch_links).selectinload(UserBranch.branch),
            selectinload(User.linked_students),
            selectinload(User.linked_parents),
        )

        # Determine branch filters — consolidate into a single JOIN
        branch_filter_ids: Optional[list[int]] = None
        if branch_ids_scope is not None and branch_id:
            # Admin scoped AND specific branch filter — intersection
            if branch_id in branch_ids_scope:
                branch_filter_ids = [branch_id]
            else:
                # Admin doesn't have access to this branch — return empty
                branch_filter_ids = [-1]  # impossible ID, returns nothing
        elif branch_ids_scope is not None:
            branch_filter_ids = branch_ids_scope
        elif branch_id:
            branch_filter_ids = [branch_id]

        if branch_filter_ids is not None:
            q = q.join(UserBranch, UserBranch.user_id == User.id).where(
                UserBranch.branch_id.in_(branch_filter_ids)
            ).distinct()

        # Filters
        if role and role != "all":
            q = q.where(User.role == role)
        if status and status != "all":
            q = q.where(User.status == status)
        if search:
            term = f"%{search}%"
            q = q.where(
                or_(
                    User.first_name.ilike(term),
                    User.last_name.ilike(term),
                    User.email.ilike(term),
                    User.phone.ilike(term),
                )
            )

        # Count for pagination
        count_q = select(func.count()).select_from(q.subquery())
        total_result = await self._session.execute(count_q)
        total = total_result.scalar_one()

        # Sorting
        sort_col_map = {
            "firstName": User.first_name,
            "lastName": User.last_name,
            "role": User.role,
            "createdAt": User.created_at,
            "lastLogin": User.last_login,
        }
        sort_col = sort_col_map.get(sort_by, User.created_at)
        q = q.order_by(sort_col.desc() if sort_order == "desc" else sort_col.asc())

        # Pagination
        q = q.offset((page - 1) * page_size).limit(page_size)

        result = await self._session.execute(q)
        users = list(result.scalars().all())
        return users, total

    # ─── Stats ────────────────────────────────────────────────────────────────

    async def get_stats(self, branch_ids_scope: Optional[list[int]] = None) -> dict:
        roles = ["owner", "superAdmin", "admin", "teacher", "student", "parent"]

        if branch_ids_scope is not None:
            # Use subquery to get distinct user IDs in scope first
            scoped_user_ids = (
                select(UserBranch.user_id)
                .where(UserBranch.branch_id.in_(branch_ids_scope))
                .distinct()
                .scalar_subquery()
            )
            q_base = select(User.role, User.status, func.count(User.id)).where(
                User.id.in_(scoped_user_ids)
            ).group_by(User.role, User.status)
        else:
            q_base = select(User.role, User.status, func.count(User.id)).group_by(
                User.role, User.status
            )

        result = await self._session.execute(q_base)
        rows = result.all()

        by_role: dict[str, int] = {r: 0 for r in roles}
        total = active = inactive = 0
        for role, status, cnt in rows:
            by_role[role] = by_role.get(role, 0) + cnt
            total += cnt
            if status == "active":
                active += cnt
            else:
                inactive += cnt

        return {"total": total, "active": active, "inactive": inactive, "by_role": by_role}

    # ─── Owner count guard ────────────────────────────────────────────────────

    async def count_owners(self) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(User).where(User.role == "owner")
        )
        return result.scalar_one()

    # ─── CRUD ─────────────────────────────────────────────────────────────────

    async def create(self, user: User) -> User:
        self._session.add(user)
        await self._session.flush()
        await self._session.refresh(user)
        return user

    async def save(self, user: User) -> User:
        merged = await self._session.merge(user)
        await self._session.flush()
        await self._session.refresh(merged)
        return merged

    async def delete(self, user: User) -> None:
        await self._session.delete(user)
        await self._session.flush()

    # ─── Branch assignment ────────────────────────────────────────────────────

    async def set_branch_assignments(self, user_id: int, branch_ids: list[int]) -> None:
        """Full replace: delete existing, insert new."""
        await self._session.execute(
            delete(UserBranch).where(UserBranch.user_id == user_id)
        )
        for branch_id in branch_ids:
            self._session.add(UserBranch(user_id=user_id, branch_id=branch_id))
        await self._session.flush()

    async def get_branch_ids(self, user_id: int) -> list[int]:
        result = await self._session.execute(
            select(UserBranch.branch_id).where(UserBranch.user_id == user_id)
        )
        return [row[0] for row in result.all()]

    # ─── Parent-student links ─────────────────────────────────────────────────

    async def link_exists(self, parent_id: int, student_id: int) -> bool:
        result = await self._session.execute(
            select(func.count())
            .select_from(ParentStudentLink)
            .where(
                and_(
                    ParentStudentLink.parent_id == parent_id,
                    ParentStudentLink.student_id == student_id,
                )
            )
        )
        return result.scalar_one() > 0

    async def create_link(self, link: ParentStudentLink) -> ParentStudentLink:
        self._session.add(link)
        await self._session.flush()
        await self._session.refresh(link)
        return link

    async def get_link_by_id(self, link_id: int) -> Optional[ParentStudentLink]:
        result = await self._session.execute(
            select(ParentStudentLink).where(ParentStudentLink.id == link_id)
        )
        return result.scalar_one_or_none()

    async def delete_link(self, link: ParentStudentLink) -> None:
        await self._session.delete(link)
        await self._session.flush()

    # ─── Branch lookup ────────────────────────────────────────────────────────

    async def get_branches_by_ids(self, branch_ids: list[int]):
        from src.modules.branches.models import Branch
        result = await self._session.execute(
            select(Branch).where(Branch.id.in_(branch_ids))
        )
        return list(result.scalars().all())
