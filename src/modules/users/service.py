"""
Users service — Sprint 1.
All business logic lives here; router is kept thin.
"""
import secrets
import string
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.common.email import send_email
from src.common.pagination import build_pagination
from src.core.security import hash_password, verify_password
from src.modules.audit.service import log_action
from src.modules.notifications.service import create_notification
from src.modules.users.exceptions import (
    AdminRequiresBranch,
    CannotDeleteLastOwner,
    CannotDeleteSelf,
    EmailOrPhoneTaken,
    LinkAlreadyExists,
    ParentRequiresStudent,
    UserHasActiveDependencies,
    UserNotFound,
)
from src.modules.users.models import ParentStudentLink, User
from src.modules.users.repository import UserRepository
from src.modules.users.schemas import (
    BranchBasic,
    ParentLinkBasic,
    PermissionsSchema,
    PrintInfoResponse,
    UserDetailResponse,
    UserResponse,
    UserWithPasswordResponse,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _generate_temp_password(length: int = 12) -> str:
    """Generate a temporary password satisfying the policy."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(c.isupper() for c in pwd)
            and any(c.islower() for c in pwd)
            and any(c.isdigit() for c in pwd)
            and any(c in "!@#$%^&*" for c in pwd)
        ):
            return pwd


def _build_user_response(user: User) -> dict:
    """Convert ORM User → camelCase dict for API response."""
    assigned_branches = [
        BranchBasic(id=ub.branch_id, name=ub.branch.name if ub.branch else "")
        for ub in (user.branch_links or [])
    ]
    linked_students = [
        ParentLinkBasic(
            id=lnk.id,
            parent_id=lnk.parent_id,
            student_id=lnk.student_id,
            relationship=lnk.relationship,
            created_at=lnk.created_at,
        )
        for lnk in (user.linked_students or [])
    ]
    linked_parents = [
        ParentLinkBasic(
            id=lnk.id,
            parent_id=lnk.parent_id,
            student_id=lnk.student_id,
            relationship=lnk.relationship,
            created_at=lnk.created_at,
        )
        for lnk in (user.linked_parents or [])
    ]
    permissions = None
    if user.role == "admin" and user.permissions:
        permissions = PermissionsSchema(**user.permissions)

    return UserResponse(
        id=user.id,
        email=user.email,
        phone=user.phone,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role,
        status=user.status,
        avatar_url=user.avatar_url,
        date_of_birth=user.date_of_birth,
        gender=user.gender,
        language=user.language,
        must_change_password=user.must_change_password,
        notifications_enabled=user.notifications_enabled,
        default_commission_percent=float(user.default_commission_percent)
        if user.default_commission_percent is not None
        else None,
        permissions=permissions,
        assigned_branches=assigned_branches,
        linked_students=linked_students,
        linked_parents=linked_parents,
        children_count=len(linked_students),
        created_by=user.created_by,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login=user.last_login,
    )


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = UserRepository(session)

    # ─── List ─────────────────────────────────────────────────────────────────

    async def list_users(
        self,
        *,
        actor: User,
        role: Optional[str] = None,
        status: Optional[str] = None,
        branch_id: Optional[int] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
        sort_by: str = "createdAt",
        sort_order: str = "desc",
    ) -> dict:
        # Branch scope for admin
        branch_ids_scope = None
        if actor.role == "admin":
            branch_ids_scope = [ub.branch_id for ub in (actor.branch_links or [])]

        users, total = await self._repo.list_users(
            role=role,
            status=status,
            branch_id=branch_id,
            search=search,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
            branch_ids_scope=branch_ids_scope,
        )
        stats = await self._repo.get_stats(branch_ids_scope=branch_ids_scope)
        pagination = build_pagination(page, page_size, total)
        return {
            "items": [_build_user_response(u) for u in users],
            "pagination": pagination,
            "stats": stats,
        }

    # ─── Get single ───────────────────────────────────────────────────────────

    async def get_user(self, user_id: int, actor: User) -> User:
        user = await self._repo.get_by_id(user_id)
        if not user:
            raise UserNotFound()

        # Branch scope check for admin
        if actor.role == "admin":
            actor_branch_ids = [ub.branch_id for ub in (actor.branch_links or [])]
            user_branch_ids = [ub.branch_id for ub in (user.branch_links or [])]
            if not any(b in actor_branch_ids for b in user_branch_ids):
                from src.core.exceptions import ForbiddenBranch
                raise ForbiddenBranch()

        return user

    # ─── Create ───────────────────────────────────────────────────────────────

    async def create_user(self, data: dict, actor: User, ip: Optional[str] = None) -> dict:
        role = data["role"]
        email = (data.get("email") or "").strip() or None
        phone = (data.get("phone") or "").strip() or None

        # At least one of email/phone required
        if not email and not phone:
            from src.core.exceptions import ValidationError
            raise ValidationError(
                message="At least one of email or phone is required.",
                details=[{"field": "email", "message": "email or phone required"}],
            )

        # Role creation authorization
        if actor.role == "admin" and role in ("owner", "superAdmin", "admin"):
            from src.core.exceptions import PermissionDenied
            raise PermissionDenied(message="Admins cannot create owner, superAdmin, or admin accounts.")
        if actor.role == "superAdmin" and role == "owner":
            from src.core.exceptions import PermissionDenied
            raise PermissionDenied(message="SuperAdmins cannot create owner accounts.")

        # Uniqueness checks
        if email and await self._repo.email_exists(email):
            raise EmailOrPhoneTaken()
        if phone and await self._repo.phone_exists(phone):
            raise EmailOrPhoneTaken()

        # Admin requires ≥1 branch + ≥1 permission flag
        if role == "admin":
            if not data.get("branch_ids"):
                raise AdminRequiresBranch()
            perms = data.get("permissions") or {}
            if not any(perms.values()):
                raise AdminRequiresBranch(
                    message="An admin must have at least one permission flag enabled."
                )

        # Parent requires ≥1 linked student
        if role == "parent" and not data.get("linked_student_ids"):
            raise ParentRequiresStudent()

        # Generate temp password
        temp_password = _generate_temp_password()

        new_user = User(
            email=email,
            phone=phone,
            password_hash=hash_password(temp_password),
            first_name=data["first_name"],
            last_name=data["last_name"],
            role=role,
            status="active",
            gender=data.get("gender"),
            date_of_birth=data.get("date_of_birth"),
            language=data.get("language", "ar"),
            must_change_password=True,
            notifications_enabled=True,
            permissions=data.get("permissions") or {},
            default_commission_percent=data.get("default_commission_percent"),
            created_by=actor.id,
        )

        new_user = await self._repo.create(new_user)

        # Branch assignments
        branch_ids = data.get("branch_ids") or []
        if branch_ids:
            await self._repo.set_branch_assignments(new_user.id, branch_ids)

        # Parent-student links
        for student_id in (data.get("linked_student_ids") or []):
            relationship = (data.get("relationships") or {}).get(str(student_id), "parent")
            link = ParentStudentLink(
                parent_id=new_user.id,
                student_id=student_id,
                relationship=relationship,
                created_by=actor.id,
            )
            self._session.add(link)

        await self._session.flush()

        # Activity log
        await log_action(
            self._session,
            user_id=actor.id,
            action="USER_CREATED",
            category="users",
            entity_type="user",
            entity_id=new_user.id,
            metadata={
                "role": role,
                "firstName": new_user.first_name,
                "lastName": new_user.last_name,
                "branchIds": branch_ids,
            },
            ip_address=ip,
        )

        # In-app notification for new user
        await create_notification(
            self._session,
            user_id=new_user.id,
            type="account_created",
            title="تم إنشاء حسابك",
            message=f"مرحباً {new_user.first_name}، تم إنشاء حسابك بنجاح.",
            link="/dashboard",
        )

        # Email (fire-and-forget; do NOT await blocking)
        if email:
            from asyncio import ensure_future
            ensure_future(
                send_email(
                    "account_created",
                    email,
                    firstName=new_user.first_name,
                    lastName=new_user.last_name,
                    temporaryPassword=temp_password,
                    identifier=email or phone,
                )
            )

        # Reload fresh with relationships
        user = await self._repo.get_by_id(new_user.id)
        response = _build_user_response(user)

        # Attach temporary password (one-time)
        return UserWithPasswordResponse(
            **response.model_dump(),
            deactivated_at=None,
            deactivated_by=None,
            children=[],
            parents=[],
            temporary_password=temp_password,
        )

    # ─── Update ───────────────────────────────────────────────────────────────

    async def update_user(
        self,
        user_id: int,
        data: dict,
        actor: User,
        ip: Optional[str] = None,
    ) -> UserResponse:
        user = await self._repo.get_by_id(user_id)
        if not user:
            raise UserNotFound()

        # Uniqueness checks
        new_email = data.get("email")
        new_phone = data.get("phone")
        if new_email and await self._repo.email_exists(new_email, exclude_id=user_id):
            raise EmailOrPhoneTaken()
        if new_phone and await self._repo.phone_exists(new_phone, exclude_id=user_id):
            raise EmailOrPhoneTaken()

        # Track changed fields for log
        changed: list[str] = []

        for field in (
            "first_name", "last_name", "email", "phone", "language",
            "gender", "date_of_birth", "avatar_url", "notifications_enabled",
        ):
            if field in data and data[field] is not None:
                setattr(user, field, data[field])
                changed.append(field)

        # Admin-only fields — only actor with elevated role can set these
        if actor.role in ("owner", "superAdmin") or (
            actor.role == "admin" and actor.id != user_id
        ):
            if "default_commission_percent" in data:
                user.default_commission_percent = data["default_commission_percent"]
                changed.append("defaultCommissionPercent")
            if "permissions" in data and data["permissions"] is not None:
                user.permissions = data["permissions"]
                changed.append("permissions")
            if "branch_ids" in data and data["branch_ids"] is not None:
                await self._repo.set_branch_assignments(user_id, data["branch_ids"])
                changed.append("branchIds")

        user = await self._repo.save(user)

        await log_action(
            self._session,
            user_id=actor.id,
            action="USER_UPDATED",
            category="users",
            entity_type="user",
            entity_id=user_id,
            metadata={"changedFields": changed},
            ip_address=ip,
        )

        return _build_user_response(user)

    # ─── Set status ───────────────────────────────────────────────────────────

    async def set_status(
        self,
        user_id: int,
        new_status: str,
        actor: User,
        ip: Optional[str] = None,
    ) -> dict:
        if actor.id == user_id:
            raise CannotDeleteSelf()

        user = await self._repo.get_by_id(user_id)
        if not user:
            raise UserNotFound()

        previous_status = user.status
        user.status = new_status
        if new_status == "inactive":
            user.deactivated_at = datetime.now(timezone.utc)
            user.deactivated_by = actor.id
            # Revoke all auth sessions
            await _revoke_all_sessions(self._session, user_id)
        else:
            user.deactivated_at = None
            user.deactivated_by = None

        await self._repo.save(user)

        await log_action(
            self._session,
            user_id=actor.id,
            action="USER_STATUS_CHANGED",
            category="users",
            entity_type="user",
            entity_id=user_id,
            metadata={"newStatus": new_status, "previousStatus": previous_status},
            ip_address=ip,
        )

        return {"id": user_id, "status": new_status}

    # ─── Reset password ───────────────────────────────────────────────────────

    async def reset_password(
        self,
        user_id: int,
        actor: User,
        ip: Optional[str] = None,
    ) -> str:
        user = await self._repo.get_by_id(user_id)
        if not user:
            raise UserNotFound()

        temp_password = _generate_temp_password()
        user.password_hash = hash_password(temp_password)
        user.must_change_password = True
        await self._repo.save(user)
        await _revoke_all_sessions(self._session, user_id)

        await log_action(
            self._session,
            user_id=actor.id,
            action="PASSWORD_CHANGED",
            category="auth",
            entity_type="user",
            entity_id=user_id,
            metadata={"resetBy": actor.id},
            ip_address=ip,
        )

        return temp_password

    # ─── Delete ───────────────────────────────────────────────────────────────

    async def delete_user(
        self,
        user_id: int,
        actor: User,
        ip: Optional[str] = None,
    ) -> None:
        if actor.id == user_id:
            raise CannotDeleteSelf()

        user = await self._repo.get_by_id(user_id)
        if not user:
            raise UserNotFound()

        if user.role == "owner" and await self._repo.count_owners() <= 1:
            raise CannotDeleteLastOwner()

        await log_action(
            self._session,
            user_id=actor.id,
            action="USER_DELETED",
            category="users",
            entity_type="user",
            entity_id=user_id,
            metadata={
                "role": user.role,
                "firstName": user.first_name,
                "lastName": user.last_name,
            },
            ip_address=ip,
        )

        await self._repo.delete(user)

    # ─── Bulk actions ─────────────────────────────────────────────────────────

    async def bulk_action(
        self,
        action: str,
        user_ids: list[int],
        actor: User,
        ip: Optional[str] = None,
    ) -> dict:
        # Silently exclude self
        safe_ids = [uid for uid in user_ids if uid != actor.id]
        skipped = len(user_ids) - len(safe_ids)

        results = []
        for uid in safe_ids:
            try:
                if action == "activate":
                    await self.set_status(uid, "active", actor, ip)
                elif action == "deactivate":
                    await self.set_status(uid, "inactive", actor, ip)
                elif action == "delete":
                    await self.delete_user(uid, actor, ip)
                elif action == "reset-passwords":
                    temp = await self.reset_password(uid, actor, ip)
                    results.append({"id": uid, "temporaryPassword": temp})
            except Exception:
                skipped += 1

        await log_action(
            self._session,
            user_id=actor.id,
            action="USER_BULK_ACTION",
            category="users",
            metadata={"action": action, "count": len(safe_ids), "userIds": safe_ids},
            ip_address=ip,
        )

        return {"processed": len(safe_ids) - skipped + (len(user_ids) - len(safe_ids)),
                "skipped": skipped,
                "results": results or None}

    # ─── Parent links ─────────────────────────────────────────────────────────

    async def create_parent_link(
        self,
        parent_id: int,
        student_id: int,
        relationship: str,
        actor: User,
        ip: Optional[str] = None,
    ) -> ParentStudentLink:
        parent = await self._repo.get_by_id(parent_id)
        if not parent or parent.role != "parent":
            raise UserNotFound(message="Parent user not found.")

        student = await self._repo.get_by_id(student_id)
        if not student or student.role != "student":
            raise UserNotFound(message="Student user not found.")

        if await self._repo.link_exists(parent_id, student_id):
            raise LinkAlreadyExists()

        link = ParentStudentLink(
            parent_id=parent_id,
            student_id=student_id,
            relationship=relationship,
            created_by=actor.id,
        )
        link = await self._repo.create_link(link)

        await log_action(
            self._session,
            user_id=actor.id,
            action="PARENT_LINKED",
            category="users",
            entity_type="parent_student_links",
            entity_id=link.id,
            metadata={"parentId": parent_id, "studentId": student_id, "relationship": relationship},
            ip_address=ip,
        )

        return link

    async def delete_parent_link(
        self,
        link_id: int,
        actor: User,
        ip: Optional[str] = None,
    ) -> None:
        link = await self._repo.get_link_by_id(link_id)
        if not link:
            raise UserNotFound(message="Link not found.")

        await log_action(
            self._session,
            user_id=actor.id,
            action="PARENT_UNLINKED",
            category="users",
            entity_type="parent_student_links",
            entity_id=link_id,
            metadata={"parentId": link.parent_id, "studentId": link.student_id},
            ip_address=ip,
        )

        await self._repo.delete_link(link)

    # ─── Print info ───────────────────────────────────────────────────────────

    async def get_print_info(self, user_id: int, actor: User) -> dict:
        user = await self._repo.get_by_id(user_id)
        if not user:
            raise UserNotFound()

        # If actor is requesting own info → allowed; otherwise needs admin role
        if actor.id != user_id and actor.role not in ("owner", "superAdmin", "admin"):
            from src.core.exceptions import PermissionDenied
            raise PermissionDenied()

        from src.core.config import settings as app_settings

        assigned_branches = [
            {"id": ub.branch_id, "name": ub.branch.name if ub.branch else ""}
            for ub in (user.branch_links or [])
        ]

        return {
            "id": user.id,
            "fullName": f"{user.first_name} {user.last_name}",
            "role": user.role,
            "email": user.email,
            "phone": user.phone,
            "assignedBranches": assigned_branches,
            "temporaryPassword": None,  # Only non-null after reset-password action
            "schoolName": "Académie Al-Nour",
            "printedAt": datetime.now(timezone.utc).isoformat(),
        }


# ─── Auth session revocation helper ─────────────────────────────────────────

async def _revoke_all_sessions(session: AsyncSession, user_id: int) -> None:
    """Revoke all refresh token sessions for a user."""
    from datetime import datetime, timezone
    from sqlalchemy import update
    from src.modules.auth.models import SessionAuth

    await session.execute(
        update(SessionAuth)
        .where(SessionAuth.user_id == user_id, SessionAuth.revoked_at.is_(None))
        .values(revoked_at=datetime.now(timezone.utc))
    )
    await session.flush()
