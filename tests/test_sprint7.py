"""
Sprint 7 backend endpoint tests.

These tests are local-only: set TEST_DATABASE_URL to a disposable local database.
The fixture refuses to run against a database whose name does not contain "test".
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
import os
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.app import create_app
from src.core.database import Base, get_db
from src.core.security import create_access_token
from src.modules.attendance.models import Attendance  # noqa: F401
from src.modules.auth.models import PasswordResetToken, SessionAuth  # noqa: F401
from src.modules.branches.models import Branch
from src.modules.classes.models import Class
from src.modules.config.models import SystemConfig
from src.modules.enrollments.models import Enrollment
from src.modules.enrollments.visitor_models import VisitorEnrollmentRequest  # noqa: F401
from src.modules.groups.models import Group
from src.modules.landing.models import LandingPageContent  # noqa: F401
from src.modules.modules.models import Module
from src.modules.notifications.models import Notification  # noqa: F401
from src.modules.payments.models import Payment  # noqa: F401
from src.modules.sessions.models import Session
from src.modules.sessions.reschedule_models import SessionRescheduleRequest  # noqa: F401
from src.modules.subscriptions.models import Subscription
from src.modules.users.models import ParentStudentLink, User, UserBranch  # noqa: F401


pytestmark = pytest.mark.asyncio

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres1:password1@localhost:5432/psp_sprint7_test",
)


def _assert_local_test_database(url: str) -> None:
    parsed = make_url(url)
    db_name = parsed.database or ""
    host = parsed.host or ""
    if "test" not in db_name.lower():
        raise RuntimeError("Refusing to run Sprint 7 tests against a non-test database.")
    if host not in {"localhost", "127.0.0.1", "postgres_db"}:
        raise RuntimeError("Refusing to run Sprint 7 tests against a non-local database.")


def _future_date(days: int = 60) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


async def _seed(db) -> dict:
    suffix = uuid.uuid4().hex[:8]
    now = datetime.now(timezone.utc)

    owner = User(
        email=f"owner-{suffix}@test.local",
        phone=f"1000{suffix}",
        password_hash="test",
        first_name="Owner",
        last_name="User",
        role="owner",
        status="active",
        permissions={},
    )
    admin = User(
        email=f"admin-{suffix}@test.local",
        phone=f"2000{suffix}",
        password_hash="test",
        first_name="Admin",
        last_name="Sessions",
        role="admin",
        status="active",
        permissions={"manageSessions": True},
    )
    teacher = User(
        email=f"teacher-{suffix}@test.local",
        phone=f"3000{suffix}",
        password_hash="test",
        first_name="Teacher",
        last_name="Main",
        role="teacher",
        status="active",
        permissions={},
    )
    other_teacher = User(
        email=f"other-teacher-{suffix}@test.local",
        phone=f"4000{suffix}",
        password_hash="test",
        first_name="Teacher",
        last_name="Other",
        role="teacher",
        status="active",
        permissions={},
    )
    student_session = User(
        email=f"student-session-{suffix}@test.local",
        phone=f"5000{suffix}",
        password_hash="test",
        first_name="Session",
        last_name="Student",
        role="student",
        status="active",
        permissions={},
    )
    student_monthly = User(
        email=f"student-monthly-{suffix}@test.local",
        phone=f"6000{suffix}",
        password_hash="test",
        first_name="Monthly",
        last_name="Student",
        role="student",
        status="active",
        permissions={},
    )
    student_expired = User(
        email=f"student-expired-{suffix}@test.local",
        phone=f"7000{suffix}",
        password_hash="test",
        first_name="Expired",
        last_name="Student",
        role="student",
        status="active",
        permissions={},
    )
    db.add_all(
        [
            owner,
            admin,
            teacher,
            other_teacher,
            student_session,
            student_monthly,
            student_expired,
        ]
    )
    await db.flush()

    branch = Branch(name=f"Sprint 7 Branch {suffix}", photo_urls=[])
    other_branch = Branch(name=f"Sprint 7 Other Branch {suffix}", photo_urls=[])
    db.add_all([branch, other_branch])
    await db.flush()

    db.add(UserBranch(user_id=admin.id, branch_id=branch.id))
    module = Module(name=f"Sprint 7 Module {suffix}", category="test")
    db.add(module)
    await db.flush()

    cls = Class(
        branch_id=branch.id,
        module_id=module.id,
        teacher_id=teacher.id,
        name=f"Sprint 7 Class {suffix}",
        status="active",
    )
    other_cls = Class(
        branch_id=other_branch.id,
        module_id=module.id,
        teacher_id=other_teacher.id,
        name=f"Sprint 7 Other Class {suffix}",
        status="active",
    )
    db.add_all([cls, other_cls])
    await db.flush()

    group = Group(
        class_id=cls.id,
        name=f"Sprint 7 Group {suffix}",
        teacher_id=teacher.id,
        schedule=[],
        room="Room 1",
        max_students=10,
        price=1000,
        subscription_type="session_based",
        session_count=8,
        status="active",
    )
    other_group = Group(
        class_id=other_cls.id,
        name=f"Sprint 7 Other Group {suffix}",
        teacher_id=other_teacher.id,
        schedule=[],
        room="Room 9",
        max_students=10,
        price=1000,
        subscription_type="session_based",
        session_count=8,
        status="active",
    )
    db.add_all([group, other_group])
    await db.flush()

    enrollment_session = Enrollment(
        group_id=group.id,
        branch_id=branch.id,
        student_id=student_session.id,
        status="active",
        source="admin",
        enrolled_by=owner.id,
        activated_at=now,
    )
    enrollment_monthly = Enrollment(
        group_id=group.id,
        branch_id=branch.id,
        student_id=student_monthly.id,
        status="active",
        source="admin",
        enrolled_by=owner.id,
        activated_at=now,
    )
    enrollment_expired = Enrollment(
        group_id=group.id,
        branch_id=branch.id,
        student_id=student_expired.id,
        status="active",
        source="admin",
        enrolled_by=owner.id,
        activated_at=now,
    )
    db.add_all([enrollment_session, enrollment_monthly, enrollment_expired])
    await db.flush()

    db.add_all(
        [
            Subscription(
                enrollment_id=enrollment_session.id,
                student_id=student_session.id,
                group_id=group.id,
                branch_id=branch.id,
                teacher_id=teacher.id,
                module_id=module.id,
                type="session_based",
                status="active",
                price=1000,
                commission_percent=0,
                commission_amount=0,
                net_amount=1000,
                total_sessions=8,
                remaining_sessions=2,
                extension_log=[],
                activated_at=now,
            ),
            Subscription(
                enrollment_id=enrollment_monthly.id,
                student_id=student_monthly.id,
                group_id=group.id,
                branch_id=branch.id,
                teacher_id=teacher.id,
                module_id=module.id,
                type="monthly",
                status="active",
                price=1000,
                commission_percent=0,
                commission_amount=0,
                net_amount=1000,
                start_date=date.today(),
                end_date=date.today() + timedelta(days=30),
                extension_log=[],
                activated_at=now,
            ),
            Subscription(
                enrollment_id=enrollment_expired.id,
                student_id=student_expired.id,
                group_id=group.id,
                branch_id=branch.id,
                teacher_id=teacher.id,
                module_id=module.id,
                type="session_based",
                status="active",
                price=1000,
                commission_percent=0,
                commission_amount=0,
                net_amount=1000,
                total_sessions=8,
                remaining_sessions=0,
                extension_log=[],
                activated_at=now,
            ),
        ]
    )

    yesterday = date.today() - timedelta(days=1)
    tomorrow = date.today() + timedelta(days=1)
    future_2 = date.today() + timedelta(days=2)
    sessions = [
        Session(
            group_id=group.id,
            branch_id=branch.id,
            session_date=yesterday,
            start_time=time(10, 0),
            end_time=time(11, 30),
            room="Room 1",
            status="scheduled",
        ),
        Session(
            group_id=group.id,
            branch_id=branch.id,
            session_date=tomorrow,
            start_time=time(10, 0),
            end_time=time(11, 30),
            room="Room 1",
            status="scheduled",
        ),
        Session(
            group_id=other_group.id,
            branch_id=other_branch.id,
            session_date=yesterday,
            start_time=time(10, 0),
            end_time=time(11, 30),
            room="Room 9",
            status="scheduled",
        ),
        Session(
            group_id=group.id,
            branch_id=branch.id,
            session_date=yesterday,
            start_time=time(12, 0),
            end_time=time(13, 30),
            room="Room 1",
            status="completed",
        ),
        Session(
            group_id=group.id,
            branch_id=branch.id,
            session_date=future_2,
            start_time=time(14, 0),
            end_time=time(15, 30),
            room="Room 1",
            status="scheduled",
        ),
        Session(
            group_id=group.id,
            branch_id=branch.id,
            session_date=future_2 + timedelta(days=1),
            start_time=time(14, 0),
            end_time=time(15, 30),
            room="Room 1",
            status="scheduled",
        ),
        Session(
            group_id=group.id,
            branch_id=branch.id,
            session_date=future_2 + timedelta(days=2),
            start_time=time(14, 0),
            end_time=time(15, 30),
            room="Room 1",
            status="scheduled",
        ),
        Session(
            group_id=group.id,
            branch_id=branch.id,
            session_date=future_2 + timedelta(days=3),
            start_time=time(14, 0),
            end_time=time(15, 30),
            room="Room 1",
            status="scheduled",
        ),
    ]
    db.add_all(sessions)
    db.add(SystemConfig())
    await db.flush()

    return {
        "owner_token": create_access_token({"sub": str(owner.id)}),
        "admin_manage_sessions_token": create_access_token({"sub": str(admin.id)}),
        "teacher_token": create_access_token({"sub": str(teacher.id)}),
        "group_id": group.id,
        "past_session_id": sessions[0].id,
        "future_session_id": sessions[1].id,
        "other_session_id": sessions[2].id,
        "completed_session_id": sessions[3].id,
        "future_session_id_2": sessions[4].id,
        "future_session_id_for_approve": sessions[5].id,
        "future_session_id_for_direct": sessions[6].id,
        "student_with_session_sub_id": student_session.id,
        "student_with_monthly_sub_id": student_monthly.id,
        "student_with_expired_sub_id": student_expired.id,
    }


@pytest_asyncio.fixture
async def sprint7_ctx():
    _assert_local_test_database(TEST_DATABASE_URL)
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with sessionmaker() as db:
        ids = await _seed(db)
        await db.commit()

    app = create_app()

    async def override_get_db():
        async with sessionmaker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield {"client": client, "sessionmaker": sessionmaker, **ids}

    app.dependency_overrides.clear()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def client(sprint7_ctx):
    return sprint7_ctx["client"]


def _ctx_value(name: str):
    @pytest_asyncio.fixture(name=name)
    async def fixture(sprint7_ctx):
        return sprint7_ctx[name]

    return fixture


owner_token = _ctx_value("owner_token")
admin_manage_sessions_token = _ctx_value("admin_manage_sessions_token")
teacher_token = _ctx_value("teacher_token")
group_id = _ctx_value("group_id")
past_session_id = _ctx_value("past_session_id")
future_session_id = _ctx_value("future_session_id")
other_session_id = _ctx_value("other_session_id")
completed_session_id = _ctx_value("completed_session_id")
future_session_id_2 = _ctx_value("future_session_id_2")
future_session_id_for_approve = _ctx_value("future_session_id_for_approve")
future_session_id_for_direct = _ctx_value("future_session_id_for_direct")
student_with_session_sub_id = _ctx_value("student_with_session_sub_id")
student_with_monthly_sub_id = _ctx_value("student_with_monthly_sub_id")
student_with_expired_sub_id = _ctx_value("student_with_expired_sub_id")


@pytest_asyncio.fixture
async def get_subscription_remaining(sprint7_ctx):
    async def _get(student_id: int) -> int:
        async with sprint7_ctx["sessionmaker"]() as db:
            result = await db.execute(
                select(Subscription.remaining_sessions).where(
                    Subscription.student_id == student_id,
                    Subscription.type == "session_based",
                )
            )
            return result.scalar_one()

    return _get


@pytest_asyncio.fixture
async def get_monthly_sub_end_date(sprint7_ctx):
    async def _get(student_id: int) -> date:
        async with sprint7_ctx["sessionmaker"]() as db:
            result = await db.execute(
                select(Subscription.end_date).where(
                    Subscription.student_id == student_id,
                    Subscription.type == "monthly",
                )
            )
            return result.scalar_one()

    return _get


@pytest_asyncio.fixture
async def get_session_status(sprint7_ctx):
    async def _get(session_id: int) -> str:
        async with sprint7_ctx["sessionmaker"]() as db:
            result = await db.execute(
                select(Session.status).where(Session.id == session_id)
            )
            return result.scalar_one()

    return _get


async def test_get_attendance_roster_returns_200(client, owner_token, past_session_id):
    r = await client.get(
        f"/api/sessions/{past_session_id}/attendance",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert r.status_code == 200
    d = r.json()["data"]
    assert "session" in d
    assert "roster" in d
    assert "summary" in d
    assert "canMarkAttendance" in d


async def test_get_attendance_roster_future_session_cannot_mark(
    client, owner_token, future_session_id
):
    r = await client.get(
        f"/api/sessions/{future_session_id}/attendance",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert r.status_code == 200
    assert r.json()["data"]["canMarkAttendance"] is False


async def test_get_attendance_roster_teacher_can_access_own_session(
    client, teacher_token, past_session_id
):
    r = await client.get(
        f"/api/sessions/{past_session_id}/attendance",
        headers={"Authorization": f"Bearer {teacher_token}"},
    )
    assert r.status_code == 200


async def test_get_attendance_roster_teacher_cannot_access_other_session(
    client, teacher_token, other_session_id
):
    r = await client.get(
        f"/api/sessions/{other_session_id}/attendance",
        headers={"Authorization": f"Bearer {teacher_token}"},
    )
    assert r.status_code == 403


async def test_mark_attendance_present_consumes_session(
    client,
    owner_token,
    past_session_id,
    student_with_session_sub_id,
    get_subscription_remaining,
):
    before = await get_subscription_remaining(student_with_session_sub_id)
    r = await client.patch(
        f"/api/sessions/{past_session_id}/attendance",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"records": [{"studentId": student_with_session_sub_id, "status": "present"}]},
    )
    assert r.status_code == 200
    d = r.json()["data"]
    assert d["success"] is True
    assert d["changedRecords"] == 1
    assert d["records"][0]["studentId"] == student_with_session_sub_id
    assert d["records"][0]["status"] == "present"
    assert d["records"][0]["sessionConsumed"] is True
    after = await get_subscription_remaining(student_with_session_sub_id)
    assert after == before - 1


async def test_mark_attendance_absent_does_not_consume(
    client,
    owner_token,
    past_session_id,
    student_with_session_sub_id,
    get_subscription_remaining,
):
    before = await get_subscription_remaining(student_with_session_sub_id)
    r = await client.patch(
        f"/api/sessions/{past_session_id}/attendance",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"records": [{"studentId": student_with_session_sub_id, "status": "absent"}]},
    )
    assert r.status_code == 200
    d = r.json()["data"]
    assert d["success"] is True
    assert d["records"][0]["status"] == "absent"
    assert d["records"][0]["sessionConsumed"] is False
    after = await get_subscription_remaining(student_with_session_sub_id)
    assert after == before


async def test_mark_present_then_correct_to_absent_reverses_session(
    client,
    owner_token,
    past_session_id,
    student_with_session_sub_id,
    get_subscription_remaining,
):
    await client.patch(
        f"/api/sessions/{past_session_id}/attendance",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"records": [{"studentId": student_with_session_sub_id, "status": "present"}]},
    )
    after_present = await get_subscription_remaining(student_with_session_sub_id)
    await client.patch(
        f"/api/sessions/{past_session_id}/attendance",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"records": [{"studentId": student_with_session_sub_id, "status": "absent"}]},
    )
    after_absent = await get_subscription_remaining(student_with_session_sub_id)
    assert after_absent == after_present + 1


async def test_clear_attendance_with_null_status_reverses_and_unmarks(
    client,
    owner_token,
    past_session_id,
    student_with_session_sub_id,
    get_subscription_remaining,
):
    before = await get_subscription_remaining(student_with_session_sub_id)
    mark_r = await client.patch(
        f"/api/sessions/{past_session_id}/attendance",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"records": [{"studentId": student_with_session_sub_id, "status": "present"}]},
    )
    assert mark_r.status_code == 200
    after_present = await get_subscription_remaining(student_with_session_sub_id)
    assert after_present == before - 1

    clear_r = await client.patch(
        f"/api/sessions/{past_session_id}/attendance",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={
            "records": [
                {
                    "studentId": student_with_session_sub_id,
                    "status": None,
                    "overridePresent": False,
                }
            ]
        },
    )
    assert clear_r.status_code == 200
    assert clear_r.json()["data"]["records"][0]["status"] is None
    after_clear = await get_subscription_remaining(student_with_session_sub_id)
    assert after_clear == before
    roster_r = await client.get(
        f"/api/sessions/{past_session_id}/attendance",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    row = next(
        entry
        for entry in roster_r.json()["data"]["roster"]
        if entry["student"]["id"] == student_with_session_sub_id
    )
    assert row["attendance"] is None


async def test_mark_present_expired_subscription_blocked(
    client, owner_token, past_session_id, student_with_expired_sub_id
):
    r = await client.patch(
        f"/api/sessions/{past_session_id}/attendance",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"records": [{"studentId": student_with_expired_sub_id, "status": "present"}]},
    )
    assert r.status_code == 422
    body = r.json()
    assert body["error"]["code"] == "CANNOT_MARK_PRESENT_SUBSCRIPTION_EXPIRED"
    assert "details" in body["error"]
    assert any(
        d["studentId"] == student_with_expired_sub_id
        for d in body["error"]["details"]
    )


async def test_mark_present_expired_subscription_with_override_allowed_for_admin(
    client,
    admin_manage_sessions_token,
    past_session_id,
    student_with_expired_sub_id,
    get_subscription_remaining,
):
    before = await get_subscription_remaining(student_with_expired_sub_id)
    r = await client.patch(
        f"/api/sessions/{past_session_id}/attendance",
        headers={"Authorization": f"Bearer {admin_manage_sessions_token}"},
        json={
            "records": [
                {
                    "studentId": student_with_expired_sub_id,
                    "status": "present",
                    "overridePresent": True,
                }
            ]
        },
    )
    assert r.status_code == 200
    after = await get_subscription_remaining(student_with_expired_sub_id)
    assert after == before


async def test_override_silently_ignored_for_teacher(
    client, teacher_token, past_session_id, student_with_expired_sub_id
):
    r = await client.patch(
        f"/api/sessions/{past_session_id}/attendance",
        headers={"Authorization": f"Bearer {teacher_token}"},
        json={
            "records": [
                {
                    "studentId": student_with_expired_sub_id,
                    "status": "present",
                    "overridePresent": True,
                }
            ]
        },
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "CANNOT_MARK_PRESENT_SUBSCRIPTION_EXPIRED"


async def test_mark_future_session_blocked(
    client, owner_token, future_session_id, student_with_session_sub_id
):
    r = await client.patch(
        f"/api/sessions/{future_session_id}/attendance",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"records": [{"studentId": student_with_session_sub_id, "status": "present"}]},
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "ATTENDANCE_SESSION_NOT_MARKABLE"


async def test_mark_attendance_auto_completes_session(
    client, owner_token, past_session_id, student_with_session_sub_id, get_session_status
):
    r = await client.patch(
        f"/api/sessions/{past_session_id}/attendance",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"records": [{"studentId": student_with_session_sub_id, "status": "present"}]},
    )
    assert r.status_code == 200
    status = await get_session_status(past_session_id)
    assert status == "completed"


async def test_mark_attendance_monthly_not_affected(
    client, owner_token, past_session_id, student_with_monthly_sub_id, get_monthly_sub_end_date
):
    end_before = await get_monthly_sub_end_date(student_with_monthly_sub_id)
    r = await client.patch(
        f"/api/sessions/{past_session_id}/attendance",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"records": [{"studentId": student_with_monthly_sub_id, "status": "present"}]},
    )
    assert r.status_code == 200
    end_after = await get_monthly_sub_end_date(student_with_monthly_sub_id)
    assert end_before == end_after


async def test_get_attendance_matrix_200(client, owner_token, group_id):
    r = await client.get(
        f"/api/groups/{group_id}/attendance-matrix",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert r.status_code == 200
    d = r.json()["data"]
    assert "sessions" in d
    assert "students" in d
    assert "hasNextPage" in d
    assert "hasPrevPage" in d
    assert "teacherName" in d
    assert "branchName" in d
    assert "dateRangeLabel" in d
    assert d["teacherName"] == "Teacher Main"
    assert d["branchName"].startswith("Sprint 7 Branch")


async def test_get_session_detail_includes_action_flags(
    client, owner_token, past_session_id, future_session_id
):
    past_r = await client.get(
        f"/api/sessions/{past_session_id}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert past_r.status_code == 200
    past = past_r.json()["data"]
    assert past["canMarkAttendance"] is True
    assert past["canRequestReschedule"] is False
    assert past["canDirectReschedule"] is False

    future_r = await client.get(
        f"/api/sessions/{future_session_id}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert future_r.status_code == 200
    future = future_r.json()["data"]
    assert future["canMarkAttendance"] is False
    assert future["canRequestReschedule"] is True
    assert future["canDirectReschedule"] is True


async def test_get_attendance_matrix_cells_count_matches_sessions(
    client, owner_token, group_id
):
    r = await client.get(
        f"/api/groups/{group_id}/attendance-matrix",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    d = r.json()["data"]
    session_count = len(d["sessions"])
    for student_row in d["students"]:
        assert len(student_row["cells"]) == session_count


async def test_get_attendance_matrix_direction_next(client, owner_token, group_id):
    r = await client.get(
        f"/api/groups/{group_id}/attendance-matrix?direction=next",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert r.status_code == 200


async def test_get_attendance_matrix_direction_prev(client, owner_token, group_id):
    r = await client.get(
        f"/api/groups/{group_id}/attendance-matrix?direction=prev",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert r.status_code == 200


async def test_extend_subscriptions_preview_returns_items(
    client,
    owner_token,
    group_id,
    student_with_session_sub_id,
    student_with_monthly_sub_id,
):
    r = await client.get(
        f"/api/groups/{group_id}/extend-subscriptions/preview?sessionsToAdd=2&daysToAdd=5",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert r.status_code == 200
    d = r.json()["data"]
    assert "items" in d
    assert d["activeCount"] == len(d["items"])
    assert d["sessionBasedCount"] == 2
    assert d["monthlyCount"] == 1

    session_item = next(
        item for item in d["items"] if item["studentName"] == "Session Student"
    )
    assert session_item["subscriptionId"]
    assert session_item["current"] == 2
    assert session_item["afterExtension"] == 4

    monthly_item = next(
        item for item in d["items"] if item["studentName"] == "Monthly Student"
    )
    assert isinstance(monthly_item["current"], str)
    assert isinstance(monthly_item["afterExtension"], str)


async def test_bulk_extend_returns_updated_subscriptions(
    client,
    owner_token,
    group_id,
    student_with_session_sub_id,
    student_with_monthly_sub_id,
    get_monthly_sub_end_date,
):
    monthly_before = await get_monthly_sub_end_date(student_with_monthly_sub_id)
    r = await client.post(
        f"/api/groups/{group_id}/extend-subscriptions",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={
            "sessionsToAdd": 2,
            "daysToAdd": 5,
            "reason": "makeup session",
        },
    )
    assert r.status_code == 200
    d = r.json()["data"]
    assert d["extendedCount"] == 3
    assert len(d["subscriptions"]) == 3

    session_sub = next(
        sub for sub in d["subscriptions"] if sub["studentId"] == student_with_session_sub_id
    )
    assert session_sub["remainingSessions"] == 4
    assert session_sub["totalSessions"] == 10
    assert session_sub["extensionLog"][-1]["sessionsAdded"] == 2

    monthly_sub = next(
        sub for sub in d["subscriptions"] if sub["studentId"] == student_with_monthly_sub_id
    )
    assert monthly_sub["endDate"] == (monthly_before + timedelta(days=5)).isoformat()
    assert monthly_sub["extensionLog"][-1]["daysAdded"] == 5


async def test_mark_teacher_absent_success(
    client, owner_token, future_session_id, get_session_status
):
    r = await client.patch(
        f"/api/sessions/{future_session_id}/mark-teacher-absent",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"reason": "مرض مفاجئ"},
    )
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "teacher_absent"
    status = await get_session_status(future_session_id)
    assert status == "teacher_absent"


async def test_mark_teacher_absent_on_completed_session_blocked(
    client, owner_token, completed_session_id
):
    r = await client.patch(
        f"/api/sessions/{completed_session_id}/mark-teacher-absent",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={},
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "SESSION_STATUS_INVALID_FOR_ACTION"


async def test_mark_teacher_absent_teacher_cannot_access(
    client, teacher_token, future_session_id
):
    r = await client.patch(
        f"/api/sessions/{future_session_id}/mark-teacher-absent",
        headers={"Authorization": f"Bearer {teacher_token}"},
        json={},
    )
    assert r.status_code == 403


async def test_mark_teacher_absent_does_not_touch_attendance(
    client, owner_token, future_session_id
):
    r = await client.patch(
        f"/api/sessions/{future_session_id}/mark-teacher-absent",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={},
    )
    assert r.status_code == 200
    roster_r = await client.get(
        f"/api/sessions/{future_session_id}/attendance",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    d = roster_r.json()["data"]
    assert all(entry["attendance"] is None for entry in d["roster"])


async def test_create_reschedule_request_201(client, teacher_token, future_session_id):
    r = await client.post(
        f"/api/sessions/{future_session_id}/reschedule-requests",
        headers={"Authorization": f"Bearer {teacher_token}"},
        json={
            "reason": "التزام طارئ",
            "proposedDate": _future_date(80),
            "proposedStartTime": "16:00",
            "proposedEndTime": "17:30",
            "proposedRoom": "قاعة 2",
        },
    )
    assert r.status_code == 201
    d = r.json()["data"]
    assert d["status"] == "pending"
    assert d["sessionId"] == future_session_id


async def test_create_reschedule_request_duplicate_pending_blocked(
    client, teacher_token, future_session_id
):
    await client.post(
        f"/api/sessions/{future_session_id}/reschedule-requests",
        headers={"Authorization": f"Bearer {teacher_token}"},
        json={
            "reason": "test",
            "proposedDate": _future_date(80),
            "proposedStartTime": "16:00",
            "proposedEndTime": "17:30",
        },
    )
    r = await client.post(
        f"/api/sessions/{future_session_id}/reschedule-requests",
        headers={"Authorization": f"Bearer {teacher_token}"},
        json={
            "reason": "another",
            "proposedDate": _future_date(81),
            "proposedStartTime": "16:00",
            "proposedEndTime": "17:30",
        },
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "RESCHEDULE_REQUEST_ALREADY_PENDING"


async def test_create_reschedule_request_invalid_times(
    client, teacher_token, future_session_id
):
    r = await client.post(
        f"/api/sessions/{future_session_id}/reschedule-requests",
        headers={"Authorization": f"Bearer {teacher_token}"},
        json={
            "reason": "test",
            "proposedDate": _future_date(80),
            "proposedStartTime": "17:00",
            "proposedEndTime": "16:00",
        },
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "RESCHEDULE_TARGET_INVALID"


async def test_create_reschedule_request_past_session_blocked(
    client, teacher_token, past_session_id
):
    r = await client.post(
        f"/api/sessions/{past_session_id}/reschedule-requests",
        headers={"Authorization": f"Bearer {teacher_token}"},
        json={
            "reason": "test",
            "proposedDate": _future_date(80),
            "proposedStartTime": "16:00",
            "proposedEndTime": "17:30",
        },
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "SESSION_NOT_RESCHEDULABLE"


async def test_list_reschedule_requests_200(client, owner_token):
    r = await client.get(
        "/api/reschedule-requests",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert r.status_code == 200
    d = r.json()["data"]
    assert "items" in d
    assert "pagination" in d
    assert "stats" in d
    assert "pending" in d["stats"]
    assert "approved" in d["stats"]
    assert "rejected" in d["stats"]


async def test_list_reschedule_requests_teacher_cannot_access(client, teacher_token):
    r = await client.get(
        "/api/reschedule-requests",
        headers={"Authorization": f"Bearer {teacher_token}"},
    )
    assert r.status_code == 403


async def test_approve_reschedule_request(
    client, owner_token, teacher_token, future_session_id
):
    req_r = await client.post(
        f"/api/sessions/{future_session_id}/reschedule-requests",
        headers={"Authorization": f"Bearer {teacher_token}"},
        json={
            "reason": "test",
            "proposedDate": _future_date(85),
            "proposedStartTime": "16:00",
            "proposedEndTime": "17:30",
        },
    )
    req_id = req_r.json()["data"]["id"]
    r = await client.post(
        f"/api/reschedule-requests/{req_id}/approve",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert r.status_code == 200
    d = r.json()["data"]
    assert "oldSession" in d
    assert "newSession" in d
    assert d["oldSession"]["status"] == "rescheduled"
    assert d["newSession"]["status"] == "scheduled"
    assert d["newSession"]["originalSessionId"] == future_session_id


async def test_approve_already_resolved_blocked(
    client, owner_token, teacher_token, future_session_id
):
    req_r = await client.post(
        f"/api/sessions/{future_session_id}/reschedule-requests",
        headers={"Authorization": f"Bearer {teacher_token}"},
        json={
            "reason": "test",
            "proposedDate": _future_date(85),
            "proposedStartTime": "16:00",
            "proposedEndTime": "17:30",
        },
    )
    req_id = req_r.json()["data"]["id"]
    await client.post(
        f"/api/reschedule-requests/{req_id}/approve",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    r = await client.post(
        f"/api/reschedule-requests/{req_id}/approve",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "RESCHEDULE_REQUEST_ALREADY_RESOLVED"


async def test_reject_reschedule_request(
    client, owner_token, teacher_token, future_session_id, get_session_status
):
    req_r = await client.post(
        f"/api/sessions/{future_session_id}/reschedule-requests",
        headers={"Authorization": f"Bearer {teacher_token}"},
        json={
            "reason": "test",
            "proposedDate": _future_date(85),
            "proposedStartTime": "16:00",
            "proposedEndTime": "17:30",
        },
    )
    req_id = req_r.json()["data"]["id"]
    r = await client.post(
        f"/api/reschedule-requests/{req_id}/reject",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"reason": "لا توجد قاعة متاحة"},
    )
    assert r.status_code == 200
    assert r.json()["data"]["rejected"] is True
    status = await get_session_status(future_session_id)
    assert status == "scheduled"


async def test_direct_reschedule_success(client, owner_token, future_session_id):
    r = await client.patch(
        f"/api/sessions/{future_session_id}/reschedule",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={
            "newDate": _future_date(90),
            "newStartTime": "15:00",
            "newEndTime": "16:30",
        },
    )
    assert r.status_code == 200
    d = r.json()["data"]
    assert d["oldSession"]["status"] == "rescheduled"
    assert d["newSession"]["status"] == "scheduled"
    assert d["newSession"]["originalSessionId"] == future_session_id


async def test_direct_reschedule_auto_rejects_pending_request(
    client, owner_token, teacher_token, future_session_id_2
):
    req_r = await client.post(
        f"/api/sessions/{future_session_id_2}/reschedule-requests",
        headers={"Authorization": f"Bearer {teacher_token}"},
        json={
            "reason": "test",
            "proposedDate": _future_date(86),
            "proposedStartTime": "16:00",
            "proposedEndTime": "17:30",
        },
    )
    req_id = req_r.json()["data"]["id"]
    await client.patch(
        f"/api/sessions/{future_session_id_2}/reschedule",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={
            "newDate": _future_date(91),
            "newStartTime": "15:00",
            "newEndTime": "16:30",
        },
    )
    list_r = await client.get(
        "/api/reschedule-requests?status=rejected",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    rejected = [item for item in list_r.json()["data"]["items"] if item["id"] == req_id]
    assert len(rejected) == 1
    assert "إعادة جدولة مباشرة من الإدارة" in rejected[0]["rejectionReason"]


async def test_direct_reschedule_teacher_cannot_access(
    client, teacher_token, future_session_id
):
    r = await client.patch(
        f"/api/sessions/{future_session_id}/reschedule",
        headers={"Authorization": f"Bearer {teacher_token}"},
        json={
            "newDate": _future_date(90),
            "newStartTime": "15:00",
            "newEndTime": "16:30",
        },
    )
    assert r.status_code == 403


async def test_direct_reschedule_invalid_times_blocked(
    client, owner_token, future_session_id
):
    r = await client.patch(
        f"/api/sessions/{future_session_id}/reschedule",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={
            "newDate": _future_date(90),
            "newStartTime": "17:00",
            "newEndTime": "15:00",
        },
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "RESCHEDULE_TARGET_INVALID"


async def test_approve_and_direct_produce_identical_session_structure(
    client,
    owner_token,
    teacher_token,
    future_session_id_for_approve,
    future_session_id_for_direct,
):
    req_r = await client.post(
        f"/api/sessions/{future_session_id_for_approve}/reschedule-requests",
        headers={"Authorization": f"Bearer {teacher_token}"},
        json={
            "reason": "test",
            "proposedDate": _future_date(100),
            "proposedStartTime": "14:00",
            "proposedEndTime": "15:30",
        },
    )
    req_id = req_r.json()["data"]["id"]
    approve_r = await client.post(
        f"/api/reschedule-requests/{req_id}/approve",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    approved_new = approve_r.json()["data"]["newSession"]

    direct_r = await client.patch(
        f"/api/sessions/{future_session_id_for_direct}/reschedule",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={
            "newDate": _future_date(101),
            "newStartTime": "14:00",
            "newEndTime": "15:30",
        },
    )
    direct_new = direct_r.json()["data"]["newSession"]

    assert set(approved_new.keys()) == set(direct_new.keys())
    assert approved_new["status"] == direct_new["status"] == "scheduled"
    assert "originalSessionId" in approved_new
    assert "originalSessionId" in direct_new
