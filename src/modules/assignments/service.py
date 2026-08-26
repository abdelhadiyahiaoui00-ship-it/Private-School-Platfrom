from datetime import datetime, timedelta, timezone
from typing import Optional
import uuid

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.pagination import build_pagination
from src.modules.assignments.exceptions import (
    AssignmentGroupMismatch,
    AssignmentGroupsCrossClass,
    AssignmentNotEffectiveTeacher,
    AssignmentNotFound,
    AssignmentSessionScopeMultiGroupInvalid,
    StudentNotEnrolled,
)
from src.modules.assignments.models import Assignment, AssignmentFile, AssignmentSubmission
from src.modules.audit.service import log_action
from src.modules.classes.models import Class
from src.modules.enrollments.models import Enrollment
from src.modules.groups.models import Group
from src.modules.sessions.models import Session
from src.modules.users.models import User


class AssignmentService:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ─── Public API ───────────────────────────────────────────────────────────

    async def get_assignment(self, assignment_id: int, actor_id: int, is_admin: bool) -> dict:
        a = await self._get_or_404(assignment_id)
        if not is_admin:
            await self._check_effective_teacher(a.group_id, actor_id)
        return await self._build(a)

    async def list_assignments(self, actor_id: int, is_admin: bool, filters: dict, page: int, page_size: int) -> dict:
        stmt = select(Assignment)
        if not is_admin:
            stmt = self._scope_to_teacher(stmt, actor_id)

        if search := filters.get("search"):
            stmt = stmt.where(or_(Assignment.title.ilike(f"%{search}%"), Assignment.description.ilike(f"%{search}%")))
        if v := filters.get("classId"):
            stmt = stmt.where(Assignment.class_id == v)
        if v := filters.get("groupId"):
            stmt = stmt.where(Assignment.group_id == v)
        if v := filters.get("batchId"):
            stmt = stmt.where(Assignment.batch_id == v)

        now = datetime.now(timezone.utc)
        soon_hours = await self._due_soon_hours()
        soon_threshold = now + timedelta(hours=soon_hours)
        due_status = filters.get("dueStatus", "all")
        if due_status == "upcoming":
            stmt = stmt.where(and_(Assignment.due_date >= now, Assignment.due_date < soon_threshold))
        elif due_status == "due_soon":
            stmt = stmt.where(and_(Assignment.due_date < soon_threshold, Assignment.due_date >= now))
        elif due_status == "overdue":
            stmt = stmt.where(Assignment.due_date < now)
        elif due_status == "no_due_date":
            stmt = stmt.where(Assignment.due_date.is_(None))

        sort_map = {"createdAt": Assignment.created_at, "dueDate": Assignment.due_date, "title": Assignment.title, "updatedAt": Assignment.updated_at}
        sort_col = sort_map.get(filters.get("sortBy", "createdAt"), Assignment.created_at)
        stmt = stmt.order_by(sort_col.desc() if filters.get("sortOrder", "desc") == "desc" else sort_col.asc())

        total = (await self.session.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0
        result = await self.session.execute(stmt.offset((page - 1) * page_size).limit(page_size))
        items = [await self._build(a) for a in result.scalars().all()]
        stats = await self._compute_stats(actor_id, is_admin, now, soon_threshold)

        return {"items": items, "pagination": build_pagination(page, page_size, total), "stats": stats}

    async def create_assignment(self, body, actor_id: int, is_admin: bool, ip: str = None) -> dict:
        if not is_admin:
            await self._check_effective_teacher(body.group_id, actor_id)
        group = await self._get_group_or_raise(body.group_id)
        if body.session_id:
            await self._validate_session(body.session_id, [body.group_id])

        a = Assignment(group_id=body.group_id, class_id=group.class_id, title=body.title,
                       description=body.description, due_date=body.due_date,
                       session_id=body.session_id, created_by=actor_id)
        self.session.add(a)
        await self.session.flush()
        await self._save_files(a.id, body.files, actor_id)
        await self.session.commit()
        await log_action(self.session, actor_id, "ASSIGNMENT_CREATED", "assignments",
                         "assignment", a.id, metadata={"groupId": body.group_id, "title": body.title}, ip_address=ip)
        return await self._build(a)

    async def bulk_create_assignments(self, body, actor_id: int, is_admin: bool, ip: str = None) -> dict:
        group_ids = body.group_ids
        if not group_ids:
            raise AssignmentGroupMismatch()
        rows = (await self.session.execute(select(Group.class_id).where(Group.id.in_(group_ids)))).all()
        if len({r[0] for r in rows}) > 1:
            raise AssignmentGroupsCrossClass()
        if body.session_id and len(group_ids) > 1:
            raise AssignmentSessionScopeMultiGroupInvalid()
        if body.session_id:
            await self._validate_session(body.session_id, group_ids)
        if not is_admin:
            for gid in group_ids:
                await self._check_effective_teacher(gid, actor_id)

        batch_id = str(uuid.uuid4())
        assignments = []
        for gid in group_ids:
            group = await self._get_group_or_raise(gid)
            a = Assignment(batch_id=batch_id, group_id=gid, class_id=group.class_id,
                           title=body.title, description=body.description, due_date=body.due_date,
                           session_id=body.session_id, created_by=actor_id)
            self.session.add(a)
            assignments.append(a)
        await self.session.flush()
        for a in assignments:
            await self._save_files(a.id, body.files, actor_id)
        await self.session.commit()
        await log_action(self.session, actor_id, "ASSIGNMENT_BATCH_CREATED", "assignments",
                         "assignment", assignments[0].id,
                         metadata={"batchId": batch_id, "groupIds": group_ids}, ip_address=ip)
        return {"assignments": [await self._build(a) for a in assignments], "batchId": batch_id, "createdCount": len(assignments)}

    async def update_assignment(self, assignment_id: int, body, actor_id: int, is_admin: bool, ip: str = None) -> dict:
        a = await self._get_or_404(assignment_id)
        if not is_admin:
            await self._check_effective_teacher(a.group_id, actor_id)

        stmt = select(Assignment).where(Assignment.batch_id == a.batch_id) if a.batch_id else select(Assignment).where(Assignment.id == assignment_id)
        siblings = (await self.session.execute(stmt)).scalars().all()

        for s in siblings:
            if body.title is not None: s.title = body.title
            if body.description is not None: s.description = body.description
            if body.due_date is not None: s.due_date = body.due_date
            s.updated_at = datetime.now(timezone.utc)
            if body.files is not None:
                old = (await self.session.execute(select(AssignmentFile).where(AssignmentFile.assignment_id == s.id))).scalars().all()
                for f in old:
                    await self.session.delete(f)
                await self._save_files(s.id, body.files, actor_id)

        await self.session.commit()
        await log_action(self.session, actor_id, "ASSIGNMENT_UPDATED", "assignments",
                         "assignment", assignment_id,
                         metadata={"batchSize": len(siblings)}, ip_address=ip)
        return {"updated": [await self._build(s) for s in siblings]}

    async def delete_assignment(self, assignment_id: int, actor_id: int, is_admin: bool, ip: str = None) -> bool:
        a = await self._get_or_404(assignment_id)
        if not is_admin:
            await self._check_effective_teacher(a.group_id, actor_id)
        await self.session.delete(a)
        await self.session.commit()
        await log_action(self.session, actor_id, "ASSIGNMENT_DELETED", "assignments",
                         "assignment", assignment_id,
                         metadata={"title": a.title, "groupId": a.group_id}, ip_address=ip)
        return True

    async def delete_batch(self, batch_id: str, actor_id: int, is_admin: bool, ip: str = None) -> dict:
        result = await self.session.execute(select(Assignment).where(Assignment.batch_id == batch_id))
        assignments = result.scalars().all()
        if not assignments:
            raise AssignmentNotFound()
        if not is_admin:
            for a in assignments:
                await self._check_effective_teacher(a.group_id, actor_id)
        for a in assignments:
            await self.session.delete(a)
        await self.session.commit()
        await log_action(self.session, actor_id, "ASSIGNMENT_BATCH_DELETED", "assignments",
                         "assignment", assignments[0].id,
                         metadata={"batchId": batch_id, "groupCount": len(assignments)}, ip_address=ip)
        return {"deleted": True, "count": len(assignments)}

    # ─── Submissions ──────────────────────────────────────────────────────────

    async def get_submissions_roster(self, assignment_id: int, actor_id: int, is_admin: bool) -> dict:
        a = await self._get_or_404(assignment_id)
        if not is_admin:
            await self._check_effective_teacher(a.group_id, actor_id)

        enroll_res = await self.session.execute(
            select(Enrollment).where(and_(Enrollment.group_id == a.group_id, Enrollment.status == "active")))
        enrollments = enroll_res.scalars().all()
        active_ids = {e.student_id for e in enrollments}

        sub_res = await self.session.execute(
            select(AssignmentSubmission).where(AssignmentSubmission.assignment_id == assignment_id))
        all_subs = {s.student_id: s for s in sub_res.scalars().all()}

        roster = []
        submitted = late = 0
        for e in enrollments:
            sub = all_subs.get(e.student_id)
            is_late = bool(sub and a.due_date and sub.submitted_at > a.due_date)
            if sub:
                submitted += 1
                if is_late: late += 1
            roster.append({
                "student": await self._user_basic(e.student_id),
                "isCurrentlyEnrolled": True,
                "submission": self._build_sub_dict(sub, is_late) if sub else None,
            })

        for sid, sub in all_subs.items():
            if sid not in active_ids:
                is_late = bool(a.due_date and sub.submitted_at > a.due_date)
                roster.append({
                    "student": await self._user_basic(sid),
                    "isCurrentlyEnrolled": False,
                    "submission": self._build_sub_dict(sub, is_late),
                })

        return {
            "assignment": await self._build(a),
            "roster": roster,
            "summary": {"submittedCount": submitted, "notSubmittedCount": len(enrollments) - submitted, "lateCount": late, "total": len(enrollments)},
        }

    async def submit_assignment(self, assignment_id: int, student_id: int, body, actor_id: int, ip: str = None) -> dict:
        a = await self._get_or_404(assignment_id)
        enroll = (await self.session.execute(
            select(Enrollment).where(and_(Enrollment.group_id == a.group_id, Enrollment.student_id == student_id))
        )).scalar_one_or_none()
        if not enroll:
            raise StudentNotEnrolled()

        existing = (await self.session.execute(
            select(AssignmentSubmission).where(
                and_(AssignmentSubmission.assignment_id == assignment_id, AssignmentSubmission.student_id == student_id))
        )).scalar_one_or_none()

        now = datetime.now(timezone.utc)
        is_late = bool(a.due_date and now > a.due_date)
        file_data = body.file

        if existing:
            existing.submission_type = body.submission_type
            existing.response_text = body.response_text
            if file_data:
                existing.file_url = file_data.file_url
                existing.file_name = file_data.file_name
                existing.file_type = file_data.file_type
            existing.submitted_at = now
            existing.updated_at = now
            sub = existing
        else:
            sub = AssignmentSubmission(
                assignment_id=assignment_id, student_id=student_id,
                submission_type=body.submission_type, response_text=body.response_text,
                file_url=file_data.file_url if file_data else None,
                file_name=file_data.file_name if file_data else None,
                file_type=file_data.file_type if file_data else None,
                submitted_at=now, updated_at=now,
            )
            self.session.add(sub)

        await self.session.commit()
        await log_action(self.session, actor_id, "ASSIGNMENT_SUBMITTED", "assignments",
                         "assignment_submission", sub.id,
                         metadata={"assignmentId": assignment_id, "isLate": is_late}, ip_address=ip)
        return self._build_sub_dict(sub, is_late)

    async def get_my_submissions(self, student_id: int, page: int, page_size: int) -> dict:
        stmt = select(AssignmentSubmission).where(
            AssignmentSubmission.student_id == student_id
        ).order_by(AssignmentSubmission.submitted_at.desc())
        total = (await self.session.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0
        result = await self.session.execute(stmt.offset((page - 1) * page_size).limit(page_size))
        items = []
        for sub in result.scalars().all():
            a = await self._get_or_404(sub.assignment_id)
            is_late = bool(a.due_date and sub.submitted_at > a.due_date)
            entry = self._build_sub_dict(sub, is_late)
            entry["assignment"] = await self._build(a)
            items.append(entry)
        return {"items": items, "pagination": build_pagination(page, page_size, total)}

    async def get_my_classes(self, teacher_id: int) -> dict:
        owned_cls_res = await self.session.execute(
            select(Class).where(and_(Class.teacher_id == teacher_id, Class.status == "active")).order_by(Class.name))
        owned_classes = owned_cls_res.scalars().all()

        classes_list = []
        listed_group_ids: set[int] = set()
        for cls in owned_classes:
            groups_res = await self.session.execute(
                select(Group).where(and_(Group.class_id == cls.id, Group.status == "active")).order_by(Group.name))
            groups = groups_res.scalars().all()
            groups_list = []
            for g in groups:
                listed_group_ids.add(g.id)
                effective = g.teacher_id or cls.teacher_id
                is_owned = effective == teacher_id
                substitute = None
                if not is_owned and g.teacher_id:
                    sub_user = (await self.session.execute(select(User).where(User.id == g.teacher_id))).scalar_one_or_none()
                    if sub_user:
                        substitute = {"id": sub_user.id, "firstName": sub_user.first_name, "lastName": sub_user.last_name, "avatarUrl": sub_user.avatar_url}
                groups_list.append({"id": g.id, "name": g.name, "capacity": g.capacity, "isOwnedByMe": is_owned, "substitute": substitute})

            teacher_name = f"{cls.teacher.first_name} {cls.teacher.last_name}" if cls.teacher else ""
            classes_list.append({
                "id": cls.id, "name": cls.name, "teacherId": cls.teacher_id, "teacherName": teacher_name,
                "moduleId": cls.module_id, "moduleName": cls.module.name if cls.module else "", "groups": groups_list,
            })

        sub_groups_res = await self.session.execute(
            select(Group).where(and_(Group.teacher_id == teacher_id, Group.status == "active")).order_by(Group.name))
        substitute_groups = []
        for g in sub_groups_res.scalars().all():
            if g.id in listed_group_ids:
                continue
            cls = (await self.session.execute(select(Class).where(Class.id == g.class_id))).scalar_one_or_none()
            if not cls:
                continue
            substitute_groups.append({
                "id": g.id, "name": g.name, "capacity": g.capacity,
                "parentClass": {
                    "id": cls.id, "name": cls.name,
                    "moduleName": cls.module.name if cls.module else "",
                    "branchName": cls.branch.name if cls.branch else "",
                    "defaultTeacherName": f"{cls.teacher.first_name} {cls.teacher.last_name}" if cls.teacher else "",
                },
            })
        return {"classes": classes_list, "substituteGroups": substitute_groups}

    # ─── Helpers ──────────────────────────────────────────────────────────────

    async def _get_or_404(self, assignment_id: int) -> Assignment:
        a = (await self.session.execute(select(Assignment).where(Assignment.id == assignment_id))).scalar_one_or_none()
        if not a:
            raise AssignmentNotFound()
        return a

    async def _get_group_or_raise(self, group_id: int) -> Group:
        g = (await self.session.execute(select(Group).where(Group.id == group_id))).scalar_one_or_none()
        if not g:
            raise AssignmentGroupMismatch()
        return g

    async def _check_effective_teacher(self, group_id: int, actor_id: int):
        g = (await self.session.execute(select(Group).where(Group.id == group_id))).scalar_one_or_none()
        if not g:
            raise AssignmentGroupMismatch()
        cls = (await self.session.execute(select(Class).where(Class.id == g.class_id))).scalar_one_or_none()
        effective = g.teacher_id or (cls.teacher_id if cls else None)
        if effective != actor_id:
            raise AssignmentNotEffectiveTeacher()

    def _scope_to_teacher(self, stmt, teacher_id: int):
        return stmt.join(Group, Assignment.group_id == Group.id).join(Class, Assignment.class_id == Class.id).where(
            or_(Group.teacher_id == teacher_id, and_(Group.teacher_id.is_(None), Class.teacher_id == teacher_id))
        )

    async def _validate_session(self, session_id: int, group_ids: list[int]):
        s = (await self.session.execute(select(Session).where(Session.id == session_id))).scalar_one_or_none()
        if not s or s.group_id not in group_ids:
            raise AssignmentGroupMismatch()

    async def _save_files(self, assignment_id: int, files, actor_id: int):
        for f in files:
            self.session.add(AssignmentFile(
                assignment_id=assignment_id, file_url=f.file_url,
                file_type=f.file_type, file_name=f.file_name, uploaded_by=actor_id,
            ))

    async def _due_soon_hours(self) -> int:
        from src.modules.config.models import SystemConfig
        cfg = (await self.session.execute(select(SystemConfig).limit(1))).scalar_one_or_none()
        return cfg.assignment_due_soon_warning_hours if cfg else 24

    async def _compute_stats(self, actor_id: int, is_admin: bool, now: datetime, soon: datetime) -> dict:
        stmt = select(Assignment)
        if not is_admin:
            stmt = self._scope_to_teacher(stmt, actor_id)
        all_a = (await self.session.execute(stmt)).scalars().all()
        return {
            "total": len(all_a),
            "upcoming": sum(1 for a in all_a if a.due_date and now <= a.due_date),
            "dueSoon": sum(1 for a in all_a if a.due_date and now <= a.due_date < soon),
            "overdue": sum(1 for a in all_a if a.due_date and a.due_date < now),
        }

    async def _user_basic(self, user_id: int) -> dict:
        u = (await self.session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if not u:
            return {"id": user_id, "firstName": "", "lastName": "", "avatarUrl": None, "dateOfBirth": None}
        return {"id": u.id, "firstName": u.first_name, "lastName": u.last_name, "avatarUrl": u.avatar_url, "dateOfBirth": str(u.date_of_birth) if u.date_of_birth else None}

    def _build_sub_dict(self, sub: AssignmentSubmission, is_late: bool) -> dict:
        student = {"id": sub.student.id, "firstName": sub.student.first_name, "lastName": sub.student.last_name,
                   "avatarUrl": sub.student.avatar_url, "dateOfBirth": None} if sub.student else {"id": sub.student_id}
        return {
            "id": sub.id, "assignmentId": sub.assignment_id, "studentId": sub.student_id, "student": student,
            "submissionType": sub.submission_type, "responseText": sub.response_text,
            "fileUrl": sub.file_url, "fileName": sub.file_name, "fileType": sub.file_type,
            "submittedAt": sub.submitted_at.isoformat(), "updatedAt": sub.updated_at.isoformat(), "isLate": is_late,
        }

    async def _build(self, a: Assignment) -> dict:
        group = a.group or (await self.session.execute(select(Group).where(Group.id == a.group_id))).scalar_one_or_none()
        cls = a.class_ or (await self.session.execute(select(Class).where(Class.id == a.class_id))).scalar_one_or_none()
        creator = a.creator or (await self.session.execute(select(User).where(User.id == a.created_by))).scalar_one_or_none()

        files = [{"id": f.id, "fileUrl": f.file_url, "fileType": f.file_type, "fileName": f.file_name,
                  "uploadedBy": f.uploaded_by, "uploadedAt": f.uploaded_at.isoformat()} for f in (a.files or [])]
        sub_count = (await self.session.execute(select(func.count(AssignmentSubmission.id)).where(AssignmentSubmission.assignment_id == a.id))).scalar() or 0
        eligible = (await self.session.execute(select(func.count(Enrollment.id)).where(and_(Enrollment.group_id == a.group_id, Enrollment.status == "active")))).scalar() or 0

        now = datetime.now(timezone.utc)
        soon_hours = await self._due_soon_hours()
        soon = now + timedelta(hours=soon_hours)
        is_overdue = bool(a.due_date and a.due_date.replace(tzinfo=timezone.utc) < now) if a.due_date and a.due_date.tzinfo is None else bool(a.due_date and a.due_date < now)
        is_due_soon = bool(a.due_date and now <= (a.due_date.replace(tzinfo=timezone.utc) if a.due_date.tzinfo is None else a.due_date) < soon)

        groups_in_batch = 1
        if a.batch_id:
            groups_in_batch = (await self.session.execute(select(func.count(Assignment.id)).where(Assignment.batch_id == a.batch_id))).scalar() or 1

        session_date_label = None
        if a.session_id and a.session:
            s = a.session
            session_date_label = f"{s.session_date} — {str(s.start_time)[:5]}"

        branch_id = cls.branch_id if cls else 0
        branch_name = cls.branch.name if cls and cls.branch else ""
        module_name = cls.module.name if cls and cls.module else ""
        creator_name = f"{creator.first_name} {creator.last_name}" if creator else ""

        return {
            "id": a.id, "batchId": a.batch_id, "groupsInBatch": groups_in_batch,
            "groupId": group.id if group else a.group_id, "groupName": group.name if group else "",
            "classId": cls.id if cls else a.class_id, "className": cls.name if cls else "",
            "moduleName": module_name, "branchId": branch_id, "branchName": branch_name,
            "sessionId": a.session_id, "sessionDateLabel": session_date_label,
            "title": a.title, "description": a.description,
            "dueDate": a.due_date.isoformat() if a.due_date else None,
            "isOverdue": is_overdue, "isDueSoon": is_due_soon,
            "files": files, "submissionsCount": sub_count, "totalEligibleStudents": eligible,
            "createdBy": a.created_by, "createdByName": creator_name,
            "createdAt": a.created_at.isoformat(), "updatedAt": a.updated_at.isoformat(),
        }
