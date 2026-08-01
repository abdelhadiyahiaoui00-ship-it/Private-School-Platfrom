from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.common.enrollment_engine import decide_enrollment_status, promote_next_in_waitlist
from src.common.pagination import build_pagination
from src.modules.audit.service import log_action
from src.modules.enrollments.exceptions import (
    AlreadyEnrolled, CannotCancelActiveWithSubscription, EnrollmentNotFound,
    GroupFull, NotLinkedChild, ParentActionRequired,
    VisitorRequestAlreadyResolved, VisitorRequestNotFound,
)
from src.modules.enrollments.models import Enrollment
from src.modules.enrollments.repository import EnrollmentRepository, VisitorRequestRepository
from src.modules.enrollments.schemas import (
    ChildBasicResponse, EnrollmentDetailResponse, EnrollmentResponse,
    EnrollmentStats, StudentBasic, VisitorEnrollmentRequestResponse, VisitorRequestStats,
)
from src.modules.enrollments.visitor_models import VisitorEnrollmentRequest
from src.modules.groups.models import Group
from src.modules.notifications.service import create_notification
from src.modules.users.models import ParentStudentLink, User


def _get_hold_hours_from_config_sync() -> int:
    """Synchronous helper to avoid re-fetching config in tight loops."""
    return 72  # fallback; actual value fetched in service methods


async def _get_hold_hours(db: AsyncSession) -> int:
    from src.modules.config.models import SystemConfig
    result = await db.execute(select(SystemConfig).limit(1))
    config = result.scalar_one_or_none()
    return config.enrollment_reservation_hold_hours if config else 72


def _compute_is_overdue(
    enrollment: Enrollment,
    hold_hours: int,
) -> tuple[bool, Optional[datetime]]:
    """
    isOverdue: True only if pending + visitor_form + past hold window.
    reservationExpiresAt: computed for pending visitor_form enrollments only.
    """
    if enrollment.status != "pending" or enrollment.source != "visitor_form":
        return False, None
    from datetime import timedelta
    expires_at = enrollment.created_at + timedelta(hours=hold_hours)
    is_overdue = datetime.now(timezone.utc) > expires_at
    return is_overdue, expires_at


async def _build_group_info(db: AsyncSession, group_id: int) -> dict:
    """Get group + class + module + branch info for enrollment response."""
    from src.modules.classes.models import Class
    from src.modules.branches.models import Branch
    from src.modules.modules.models import Module

    group_result = await db.execute(select(Group).where(Group.id == group_id))
    group = group_result.scalar_one_or_none()
    if not group:
        return {}

    class_result = await db.execute(select(Class).where(Class.id == group.class_id))
    cls = class_result.scalar_one_or_none()

    module = None
    branch = None
    if cls:
        mod_result = await db.execute(select(Module).where(Module.id == cls.module_id))
        module = mod_result.scalar_one_or_none()
        branch_result = await db.execute(select(Branch).where(Branch.id == cls.branch_id))
        branch = branch_result.scalar_one_or_none()

    return {
        "group_name": group.name if group else "",
        "class_id": cls.id if cls else 0,
        "class_name": cls.name if cls else "",
        "module_name": module.name if module else "",
        "branch_id": cls.branch_id if cls else 0,
        "branch_name": branch.name if branch else "",
    }


async def _build_enrollment_response(
    enrollment: Enrollment,
    db: AsyncSession,
    hold_hours: int,
) -> EnrollmentResponse:
    group_info = await _build_group_info(db, enrollment.group_id)
    is_overdue, expires_at = _compute_is_overdue(enrollment, hold_hours)

    student = None
    if enrollment.student:
        student = StudentBasic(
            id=enrollment.student.id,
            first_name=enrollment.student.first_name,
            last_name=enrollment.student.last_name,
            avatar_url=enrollment.student.avatar_url,
            date_of_birth=enrollment.student.date_of_birth,
        )

    return EnrollmentResponse(
        id=enrollment.id,
        group_id=enrollment.group_id,
        group_name=group_info.get("group_name", ""),
        class_id=group_info.get("class_id", 0),
        class_name=group_info.get("class_name", ""),
        module_name=group_info.get("module_name", ""),
        branch_id=group_info.get("branch_id", 0),
        branch_name=group_info.get("branch_name", ""),
        student_id=enrollment.student_id,
        student=student,
        status=enrollment.status,
        waitlist_position=enrollment.waitlist_position,
        source=enrollment.source,
        enrolled_by=enrollment.enrolled_by,
        is_overdue=is_overdue,
        reservation_expires_at=expires_at,
        created_at=enrollment.created_at,
        updated_at=enrollment.updated_at,
        activated_at=enrollment.activated_at,
        cancelled_at=enrollment.cancelled_at,
        cancelled_reason=enrollment.cancelled_reason,
    )


class EnrollmentService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = EnrollmentRepository(session)
        self._visitor_repo = VisitorRequestRepository(session)

    def _get_branch_scope(self, actor: User) -> Optional[list[int]]:
        if actor.role == "admin":
            return [ub.branch_id for ub in (actor.branch_links or [])]
        return None

    async def _get_group_with_lock(self, group_id: int) -> Optional[Group]:
        result = await self._session.execute(
            select(Group).where(Group.id == group_id)
        )
        return result.scalar_one_or_none()

    # ─── Visitor Reservation ──────────────────────────────────────────────────

    async def create_visitor_reservation(self, data: dict, ip: Optional[str] = None) -> dict:
        """Public endpoint — no actor. Single transaction."""
        group_id = data["group_id"]

        # Validate group is active + class is active + branch is active
        from src.modules.classes.models import Class
        from src.modules.branches.models import Branch

        group = await self._get_group_with_lock(group_id)
        if not group or group.status != "active":
            from src.core.exceptions import ResourceNotFound
            raise ResourceNotFound(message="Group not found or inactive.")

        class_result = await self._session.execute(
            select(Class).where(Class.id == group.class_id)
        )
        cls = class_result.scalar_one_or_none()
        if not cls or cls.status != "active":
            from src.core.exceptions import ResourceNotFound
            raise ResourceNotFound(message="Class not found or inactive.")

        branch_result = await self._session.execute(
            select(Branch).where(Branch.id == cls.branch_id)
        )
        branch = branch_result.scalar_one_or_none()
        if not branch or not branch.is_active:
            from src.core.exceptions import ResourceNotFound
            raise ResourceNotFound(message="Branch not found or inactive.")

        # Capacity decision (with row lock)
        status, waitlist_position = await decide_enrollment_status(self._session, group)

        # Create enrollment row
        enrollment = Enrollment(
            group_id=group_id,
            branch_id=cls.branch_id,
            student_id=None,  # visitor — no user yet
            status=status,
            waitlist_position=waitlist_position,
            source="visitor_form",
            enrolled_by=None,
        )
        enrollment = await self._repo.create(enrollment)

        # Create visitor_enrollment_requests row
        visitor_req = VisitorEnrollmentRequest(
            enrollment_id=enrollment.id,
            first_name=data["first_name"],
            last_name=data["last_name"],
            date_of_birth=data["date_of_birth"],
            gender=data["gender"],
            contact_phone=data["contact_phone"],
            contact_email=data.get("contact_email") or None,
            guardian_name=data.get("guardian_name") or None,
            guardian_phone=data.get("guardian_phone") or None,
            notes=data.get("notes") or None,
            status="pending",
        )
        visitor_req = await self._visitor_repo.create(visitor_req)

        # Notify admins with manageEnrollments in this branch
        from src.modules.users.models import UserBranch
        from sqlalchemy import and_
        admin_result = await self._session.execute(
            select(User)
            .join(UserBranch, UserBranch.user_id == User.id)
            .where(
                UserBranch.branch_id == cls.branch_id,
                User.role.in_(["admin", "superAdmin", "owner"]),
                User.status == "active",
            )
        )
        admins = admin_result.scalars().all()
        for admin in admins:
            perms = admin.permissions or {}
            if admin.role in ("superAdmin", "owner") or perms.get("manageEnrollments"):
                await create_notification(
                    self._session,
                    user_id=admin.id,
                    type="visitor_request_received",
                    title="طلب تسجيل جديد من زائر",
                    message=f"طلب من {data['first_name']} {data['last_name']} للانضمام إلى {group.name}",
                    entity_type="visitor_enrollment_request",
                    entity_id=visitor_req.id,
                )

        await log_action(
            self._session,
            user_id=None,
            action="VISITOR_REQUEST_CREATED",
            category="enrollments",
            entity_type="visitor_enrollment_request",
            entity_id=visitor_req.id,
            metadata={"groupId": group_id, "firstName": data["first_name"], "lastName": data["last_name"]},
            ip_address=ip,
        )
        if status == "waitlisted":
            await log_action(
                self._session,
                user_id=None,
                action="ENROLLMENT_WAITLISTED",
                category="enrollments",
                entity_type="enrollment",
                entity_id=enrollment.id,
                metadata={"groupId": group_id, "waitlistPosition": waitlist_position},
            )

        hold_hours = await _get_hold_hours(self._session)
        _, expires_at = _compute_is_overdue(enrollment, hold_hours)

        return {
            "enrollmentId": enrollment.id,
            "visitorRequestId": visitor_req.id,
            "status": status,
            "waitlistPosition": waitlist_position,
            "groupName": group.name,
            "className": cls.name,
        }

    # ─── Authenticated Enrollment ─────────────────────────────────────────────

    async def create_enrollment(
        self, data: dict, actor: User, ip: Optional[str] = None
    ) -> EnrollmentResponse:
        group_id = data["group_id"]
        student_id_from_body = data.get("student_id")

        # Role-based studentId resolution
        if actor.role == "student":
            if student_id_from_body and student_id_from_body != actor.id:
                from src.core.exceptions import PermissionDenied
                raise PermissionDenied(message="Students can only enroll themselves.")
            student_id = actor.id
            source = "self"
        elif actor.role == "parent":
            if not student_id_from_body:
                from src.core.exceptions import ValidationError
                raise ValidationError(message="studentId is required for parent enrollment.")
            if not await self._repo.is_linked_child(actor.id, student_id_from_body):
                raise NotLinkedChild()
            student_id = student_id_from_body
            source = "parent"
        else:
            # admin / superAdmin / owner
            if not student_id_from_body:
                from src.core.exceptions import ValidationError
                raise ValidationError(message="studentId is required.")
            student_id = student_id_from_body
            source = "admin"

        # Duplicate check
        if await self._repo.has_active_enrollment(group_id, student_id):
            raise AlreadyEnrolled()

        # Get group and validate
        group = await self._get_group_with_lock(group_id)
        if not group or group.status != "active":
            from src.core.exceptions import ResourceNotFound
            raise ResourceNotFound(message="Group not found or inactive.")

        from src.modules.classes.models import Class
        class_result = await self._session.execute(
            select(Class).where(Class.id == group.class_id)
        )
        cls = class_result.scalar_one_or_none()

        # Capacity decision (with row lock)
        status, waitlist_position = await decide_enrollment_status(self._session, group)

        enrollment = Enrollment(
            group_id=group_id,
            branch_id=cls.branch_id if cls else group.class_.branch_id,
            student_id=student_id,
            status=status,
            waitlist_position=waitlist_position,
            source=source,
            enrolled_by=actor.id,
        )
        enrollment = await self._repo.create(enrollment)

        # Notifications
        await create_notification(
            self._session,
            user_id=student_id,
            type="enrollment_pending" if status == "pending" else "enrollment_waitlisted",
            title="تم التسجيل بنجاح" if status == "pending" else "تمت إضافتك لقائمة الانتظار",
            message=f"تم تسجيلك في {group.name}",
            entity_type="enrollment",
            entity_id=enrollment.id,
        )

        await log_action(
            self._session,
            user_id=actor.id,
            action="ENROLLMENT_CREATED",
            category="enrollments",
            entity_type="enrollment",
            entity_id=enrollment.id,
            metadata={"groupId": group_id, "studentId": student_id, "source": source, "status": status},
            ip_address=ip,
        )
        if status == "waitlisted":
            await log_action(
                self._session,
                user_id=None,
                action="ENROLLMENT_WAITLISTED",
                category="enrollments",
                entity_type="enrollment",
                entity_id=enrollment.id,
                metadata={"groupId": group_id, "waitlistPosition": waitlist_position},
            )

        # Reload with relationships
        enrollment = await self._repo.get_by_id(enrollment.id)
        hold_hours = await _get_hold_hours(self._session)
        return await _build_enrollment_response(enrollment, self._session, hold_hours)

    # ─── List Enrollments (admin) ─────────────────────────────────────────────

    async def list_enrollments(self, params: dict, actor: User) -> dict:
        branch_ids_scope = self._get_branch_scope(actor)
        hold_hours = await _get_hold_hours(self._session)

        enrollments, total = await self._repo.get_all(
            search=params.get("search"),
            branch_id=params.get("branch_id"),
            branch_ids_scope=branch_ids_scope,
            group_id=params.get("group_id"),
            class_id=params.get("class_id"),
            status=params.get("status"),
            source=params.get("source"),
            overdue_only=params.get("overdue_only", False),
            hold_hours=hold_hours,
            page=params.get("page", 1),
            page_size=params.get("page_size", 20),
            sort_by=params.get("sort_by", "created_at"),
            sort_order=params.get("sort_order", "desc"),
        )
        stats = await self._repo.get_stats(branch_ids_scope, hold_hours)
        items = []
        for e in enrollments:
            items.append((await _build_enrollment_response(e, self._session, hold_hours)).model_dump(by_alias=True))

        return {
            "items": items,
            "pagination": build_pagination(params.get("page", 1), params.get("page_size", 20), total),
            "stats": EnrollmentStats(**stats).model_dump(by_alias=True),
        }

    # ─── Get My Enrollments (student/parent) ─────────────────────────────────

    async def get_my_enrollments(self, actor: User, child_id: Optional[int] = None, status: Optional[str] = None) -> list[dict]:
        hold_hours = await _get_hold_hours(self._session)

        if actor.role == "student":
            enrollments = await self._repo.get_my_enrollments(
                student_id=actor.id, status=status
            )
        elif actor.role == "parent":
            if child_id:
                # Verify child is linked
                if not await self._repo.is_linked_child(actor.id, child_id):
                    raise NotLinkedChild()
                enrollments = await self._repo.get_my_enrollments(
                    student_id=child_id, status=status
                )
            else:
                # Merge all linked children
                child_ids = await self._repo.get_parent_child_ids(actor.id)
                enrollments = await self._repo.get_my_enrollments(
                    student_ids=child_ids, status=status
                )
        else:
            enrollments = []

        items = []
        for e in enrollments:
            items.append((await _build_enrollment_response(e, self._session, hold_hours)).model_dump(by_alias=True))
        return items

    # ─── Get Single Enrollment ────────────────────────────────────────────────

    async def get_enrollment(self, enrollment_id: int, actor: User) -> dict:
        enrollment = await self._repo.get_by_id(enrollment_id)
        if not enrollment:
            raise EnrollmentNotFound()
        hold_hours = await _get_hold_hours(self._session)
        base = await _build_enrollment_response(enrollment, self._session, hold_hours)

        visitor_request = None
        if enrollment.visitor_request:
            vr = enrollment.visitor_request
            visitor_request = {
                "id": vr.id,
                "firstName": vr.first_name,
                "lastName": vr.last_name,
                "contactPhone": vr.contact_phone,
                "contactEmail": vr.contact_email,
                "status": vr.status,
            }

        detail_dict = base.model_dump(by_alias=True)
        detail_dict["visitorRequest"] = visitor_request
        return detail_dict

    # ─── Cancel Enrollment ────────────────────────────────────────────────────

    async def cancel_enrollment(
        self,
        enrollment_id: int,
        actor: User,
        reason: Optional[str] = None,
        ip: Optional[str] = None,
    ) -> dict:
        enrollment = await self._repo.get_by_id(enrollment_id)
        if not enrollment:
            raise EnrollmentNotFound()

        # Permission: self, linked parent, or admin
        can_cancel = False
        if actor.role in ("owner", "superAdmin"):
            can_cancel = True
        elif actor.role == "admin":
            perms = actor.permissions or {}
            can_cancel = bool(perms.get("manageEnrollments"))
        elif actor.role == "student" and enrollment.student_id == actor.id:
            can_cancel = True
        elif actor.role == "parent":
            can_cancel = await self._repo.is_linked_child(actor.id, enrollment.student_id or -1)

        if not can_cancel:
            from src.core.exceptions import PermissionDenied
            raise PermissionDenied()

        previous_status = enrollment.status
        enrollment.status = "cancelled"
        enrollment.cancelled_at = datetime.now(timezone.utc)
        enrollment.cancelled_reason = reason
        await self._repo.save(enrollment)

        # FIFO promotion if cancelled was pending or active
        promoted = None
        if previous_status in ("pending", "active"):
            promoted_enrollment = await promote_next_in_waitlist(
                self._session, enrollment.group_id, actor.id
            )
            if promoted_enrollment:
                student_name = ""
                if promoted_enrollment.student:
                    student_name = f"{promoted_enrollment.student.first_name} {promoted_enrollment.student.last_name}"
                promoted = {
                    "enrollmentId": promoted_enrollment.id,
                    "studentName": student_name,
                    "newStatus": "pending",
                }

        await log_action(
            self._session,
            user_id=actor.id,
            action="ENROLLMENT_CANCELLED",
            category="enrollments",
            entity_type="enrollment",
            entity_id=enrollment_id,
            metadata={"groupId": enrollment.group_id, "previousStatus": previous_status, "reason": reason},
            ip_address=ip,
        )

        return {"cancelled": True, "promoted": promoted}

    # ─── Manual Promote ───────────────────────────────────────────────────────

    async def promote_enrollment(
        self, enrollment_id: int, actor: User, ip: Optional[str] = None
    ) -> EnrollmentResponse:
        enrollment = await self._repo.get_by_id(enrollment_id)
        if not enrollment:
            raise EnrollmentNotFound()
        if enrollment.status != "waitlisted":
            from src.core.exceptions import ValidationError
            raise ValidationError(message="Only waitlisted enrollments can be promoted.")

        # Check if a seat is actually available
        active_count = await self._repo.count_active_enrollments(enrollment.group_id)
        group = await self._get_group_with_lock(enrollment.group_id)
        if not group or active_count >= group.max_students:
            raise GroupFull()

        enrollment.status = "pending"
        enrollment.waitlist_position = None
        await self._repo.save(enrollment)

        await self._repo.resequence_waitlist(enrollment.group_id)

        if enrollment.student_id:
            await create_notification(
                self._session,
                user_id=enrollment.student_id,
                type="enrollment_promoted",
                title="تمت ترقيتك من قائمة الانتظار",
                message="أصبح لديك مقعد متاح. يرجى زيارة الفرع لإتمام الدفع.",
                entity_type="enrollment",
                entity_id=enrollment.id,
            )

        await log_action(
            self._session,
            user_id=actor.id,
            action="ENROLLMENT_PROMOTED",
            category="enrollments",
            entity_type="enrollment",
            entity_id=enrollment_id,
            metadata={"groupId": enrollment.group_id, "manual": True},
            ip_address=ip,
        )

        enrollment = await self._repo.get_by_id(enrollment_id)
        hold_hours = await _get_hold_hours(self._session)
        return await _build_enrollment_response(enrollment, self._session, hold_hours)

    # ─── Visitor Requests List ────────────────────────────────────────────────

    async def list_visitor_requests(self, params: dict, actor: User) -> dict:
        branch_ids_scope = self._get_branch_scope(actor)
        hold_hours = await _get_hold_hours(self._session)
        requests, total = await self._visitor_repo.get_all(
            status=params.get("status", "pending"),
            branch_id=params.get("branch_id"),
            branch_ids_scope=branch_ids_scope,
            search=params.get("search"),
            page=params.get("page", 1),
            page_size=params.get("page_size", 20),
        )
        stats = await self._visitor_repo.get_stats(branch_ids_scope)

        items = []
        for vr in requests:
            enrollment_resp = await _build_enrollment_response(vr.enrollment, self._session, hold_hours)
            item = {
                "id": vr.id,
                "firstName": vr.first_name,
                "lastName": vr.last_name,
                "contactPhone": vr.contact_phone,
                "contactEmail": vr.contact_email,
                "status": vr.status,
                "enrollmentId": vr.enrollment_id,
                "dateOfBirth": str(vr.date_of_birth),
                "gender": vr.gender,
                "guardianName": vr.guardian_name,
                "guardianPhone": vr.guardian_phone,
                "notes": vr.notes,
                "convertedToUserId": vr.converted_to_user_id,
                "createdAt": vr.created_at.isoformat(),
                "enrollment": enrollment_resp.model_dump(by_alias=True),
            }
            items.append(item)

        return {
            "items": items,
            "pagination": build_pagination(params.get("page", 1), params.get("page_size", 20), total),
            "stats": VisitorRequestStats(**stats).model_dump(by_alias=True),
        }

    # ─── Convert Visitor ──────────────────────────────────────────────────────

    async def convert_visitor(
        self,
        request_id: int,
        data: dict,
        actor: User,
        ip: Optional[str] = None,
    ) -> dict:
        visitor_req = await self._visitor_repo.get_by_id(request_id)
        if not visitor_req:
            raise VisitorRequestNotFound()
        if visitor_req.status != "pending":
            raise VisitorRequestAlreadyResolved()

        parent_action = data.get("parent_action", "none")
        if parent_action == "linkExisting" and not data.get("existing_parent_id"):
            raise ParentActionRequired(message="existingParentId is required for linkExisting.")
        if parent_action == "createNew":
            parent_data = data.get("parent") or {}
            if not parent_data.get("first_name") or (not parent_data.get("phone") and not parent_data.get("email")):
                raise ParentActionRequired(message="Parent first name and contact (phone or email) are required for createNew.")

        # Create student user via same path as POST /api/users
        from src.modules.users.service import UserService, _generate_temp_password
        from src.core.security import hash_password
        from src.modules.users.models import User as UserModel

        student_data = data.get("student", {})
        temp_password_student = _generate_temp_password()
        student_email = student_data.get("email") or None
        student_phone = student_data.get("phone") or None

        if not student_email and not student_phone:
            from src.core.exceptions import ValidationError
            raise ValidationError(message="At least one of email or phone is required for the student account.")

        new_student = UserModel(
            email=student_email,
            phone=student_phone,
            password_hash=hash_password(temp_password_student),
            first_name=student_data["first_name"],
            last_name=student_data["last_name"],
            role="student",
            status="active",
            gender=student_data.get("gender"),
            date_of_birth=student_data.get("date_of_birth"),
            language=student_data.get("language", "ar"),
            must_change_password=True,
            notifications_enabled=True,
            permissions={},
            created_by=actor.id,
        )
        self._session.add(new_student)
        await self._session.flush()
        await self._session.refresh(new_student)

        # Handle parent
        new_parent = None
        temp_password_parent = None
        from src.modules.users.models import ParentStudentLink

        if parent_action == "createNew":
            parent_dto = data.get("parent", {})
            temp_password_parent = _generate_temp_password()
            parent_email = parent_dto.get("email") or None
            parent_phone = parent_dto.get("phone") or None
            new_parent = UserModel(
                email=parent_email,
                phone=parent_phone,
                password_hash=hash_password(temp_password_parent),
                first_name=parent_dto["first_name"],
                last_name=parent_dto["last_name"],
                role="parent",
                status="active",
                language="ar",
                must_change_password=True,
                notifications_enabled=True,
                permissions={},
                created_by=actor.id,
            )
            self._session.add(new_parent)
            await self._session.flush()
            await self._session.refresh(new_parent)
            link = ParentStudentLink(
                parent_id=new_parent.id,
                student_id=new_student.id,
                relationship=parent_dto.get("relationship", "parent"),
                created_by=actor.id,
            )
            self._session.add(link)

        elif parent_action == "linkExisting":
            existing_parent_id = data["existing_parent_id"]
            link = ParentStudentLink(
                parent_id=existing_parent_id,
                student_id=new_student.id,
                relationship="parent",
                created_by=actor.id,
            )
            self._session.add(link)

        # Attach studentId to the enrollment
        enrollment = visitor_req.enrollment
        enrollment.student_id = new_student.id
        # status UNCHANGED — same seat, same row

        # Mark visitor request as converted
        visitor_req.status = "converted"
        visitor_req.converted_to_user_id = new_student.id

        await self._session.flush()

        # Notifications
        await create_notification(
            self._session,
            user_id=new_student.id,
            type="account_created",
            title="تم إنشاء حسابك",
            message=f"مرحباً {new_student.first_name}، تم إنشاء حسابك بنجاح.",
        )
        if new_parent:
            await create_notification(
                self._session,
                user_id=new_parent.id,
                type="account_created",
                title="تم إنشاء حسابك",
                message=f"مرحباً {new_parent.first_name}، تم إنشاء حسابك بنجاح.",
            )

        await log_action(
            self._session,
            user_id=actor.id,
            action="VISITOR_REQUEST_CONVERTED",
            category="enrollments",
            entity_type="visitor_enrollment_request",
            entity_id=request_id,
            metadata={"studentId": new_student.id, "parentAction": parent_action},
            ip_address=ip,
        )

        # Build responses
        hold_hours = await _get_hold_hours(self._session)
        from src.modules.users.service import _build_user_response
        from src.modules.users.repository import UserRepository
        user_repo = UserRepository(self._session)
        student_full = await user_repo.get_by_id(new_student.id)
        enrollment_full = await self._repo.get_by_id(enrollment.id)

        enrollment_resp = await _build_enrollment_response(enrollment_full, self._session, hold_hours)

        student_out = _build_user_response(student_full).model_dump(by_alias=True)
        student_out["temporaryPassword"] = temp_password_student

        parent_out = None
        if new_parent:
            parent_full = await user_repo.get_by_id(new_parent.id)
            parent_out = _build_user_response(parent_full).model_dump(by_alias=True)
            parent_out["temporaryPassword"] = temp_password_parent

        return {
            "student": student_out,
            "parent": parent_out,
            "enrollment": enrollment_resp.model_dump(by_alias=True),
        }

    # ─── Reject Visitor ───────────────────────────────────────────────────────

    async def reject_visitor(
        self,
        request_id: int,
        actor: User,
        reason: Optional[str] = None,
        ip: Optional[str] = None,
    ) -> None:
        visitor_req = await self._visitor_repo.get_by_id(request_id)
        if not visitor_req:
            raise VisitorRequestNotFound()
        if visitor_req.status != "pending":
            raise VisitorRequestAlreadyResolved()

        visitor_req.status = "rejected"
        await self._visitor_repo.save(visitor_req)

        # Cascade: cancel the linked enrollment + trigger FIFO promotion
        enrollment = visitor_req.enrollment
        previous_status = enrollment.status
        enrollment.status = "cancelled"
        enrollment.cancelled_at = datetime.now(timezone.utc)
        enrollment.cancelled_reason = reason or "visitor_request_rejected"
        await self._repo.save(enrollment)

        if previous_status in ("pending", "active"):
            await promote_next_in_waitlist(
                self._session, enrollment.group_id, actor.id
            )

        await log_action(
            self._session,
            user_id=actor.id,
            action="VISITOR_REQUEST_REJECTED",
            category="enrollments",
            entity_type="visitor_enrollment_request",
            entity_id=request_id,
            metadata={"reason": reason},
            ip_address=ip,
        )

    # ─── My Children (parent) ─────────────────────────────────────────────────

    async def get_my_children(self, actor: User) -> list[dict]:
        if actor.role != "parent":
            from src.core.exceptions import PermissionDenied
            raise PermissionDenied(message="Only parents can access this endpoint.")

        from src.modules.users.models import ParentStudentLink, User as UserModel
        result = await self._session.execute(
            select(ParentStudentLink, UserModel)
            .join(UserModel, UserModel.id == ParentStudentLink.student_id)
            .where(ParentStudentLink.parent_id == actor.id)
            .order_by(ParentStudentLink.created_at.asc())
        )
        rows = result.all()

        items = []
        for link, student in rows:
            items.append(ChildBasicResponse(
                id=student.id,
                first_name=student.first_name,
                last_name=student.last_name,
                avatar_url=student.avatar_url,
                date_of_birth=student.date_of_birth,
                relationship=link.relationship,
                link_id=link.id,
            ).model_dump(by_alias=True))

        return items
