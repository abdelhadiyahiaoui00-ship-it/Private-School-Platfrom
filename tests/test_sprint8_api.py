"""
Sprint 8 backend endpoint tests.

These tests are local-only: set TEST_DATABASE_URL to a disposable local database.
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
from src.modules.auth.models import PasswordResetToken, SessionAuth  # noqa: F401
from src.modules.branches.models import Branch
from src.modules.classes.models import Class
from src.modules.config.models import SystemConfig
from src.modules.enrollments.models import Enrollment
from src.modules.groups.models import Group
from src.modules.modules.models import Module
from src.modules.sessions.models import Session
from src.modules.subscriptions.models import Subscription
from src.modules.users.models import User, UserBranch  # noqa: F401
from src.modules.assignments.models import Assignment, AssignmentSubmission, AssignmentFile  # noqa: F401


pytestmark = pytest.mark.asyncio

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres1:password1@localhost:5432/psp_sprint8_test",
)


def _assert_local_test_database(url: str) -> None:
    parsed = make_url(url)
    db_name = parsed.database or ""
    host = parsed.host or ""
    if "test" not in db_name.lower():
        raise RuntimeError("Refusing to run tests against a non-test database.")
    if host not in {"localhost", "127.0.0.1", "postgres_db"}:
        raise RuntimeError("Refusing to run tests against a non-local database.")


async def _seed(db) -> dict:
    suffix = uuid.uuid4().hex[:8]
    now = datetime.now(timezone.utc)

    admin = User(
        email=f"admin-{suffix}@test.local",
        phone=f"1000{suffix}",
        password_hash="test",
        first_name="Admin",
        last_name="User",
        role="admin",
        status="active",
        permissions={"manageClasses": True, "manageSessions": True},
    )
    teacher = User(
        email=f"teacher-{suffix}@test.local",
        phone=f"2000{suffix}",
        password_hash="test",
        first_name="Teacher",
        last_name="Main",
        role="teacher",
        status="active",
        permissions={},
    )
    student = User(
        email=f"student-{suffix}@test.local",
        phone=f"3000{suffix}",
        password_hash="test",
        first_name="Student",
        last_name="One",
        role="student",
        status="active",
        permissions={},
    )
    db.add_all([admin, teacher, student])
    await db.flush()

    branch = Branch(name=f"Sprint 8 Branch {suffix}", photo_urls=[])
    db.add(branch)
    await db.flush()

    module = Module(name=f"Sprint 8 Module {suffix}", category="test")
    db.add(module)
    await db.flush()

    cls = Class(
        branch_id=branch.id,
        module_id=module.id,
        teacher_id=teacher.id,
        name=f"Sprint 8 Class {suffix}",
        status="active",
    )
    db.add(cls)
    await db.flush()

    group = Group(
        class_id=cls.id,
        name=f"Sprint 8 Group {suffix}",
        teacher_id=teacher.id,
        schedule=[],
        room="Room 1",
        max_students=10,
        price=1000,
        subscription_type="monthly",
        status="active",
    )
    db.add(group)
    await db.flush()

    enrollment = Enrollment(
        group_id=group.id,
        branch_id=branch.id,
        student_id=student.id,
        status="active",
        source="admin",
        enrolled_by=admin.id,
        activated_at=now,
    )
    db.add(enrollment)
    await db.flush()

    session = Session(
        group_id=group.id,
        branch_id=branch.id,
        session_date=date.today() + timedelta(days=2),
        start_time=time(10, 0),
        end_time=time(11, 30),
        room="Room 1",
        status="scheduled",
    )
    db.add(session)
    db.add(SystemConfig())
    await db.flush()

    return {
        "admin_token": create_access_token({"sub": str(admin.id)}),
        "teacher_token": create_access_token({"sub": str(teacher.id)}),
        "student_token": create_access_token({"sub": str(student.id)}),
        "student_id": student.id,
        "group_id": group.id,
        "class_id": cls.id,
        "session_id": session.id,
    }


@pytest_asyncio.fixture
async def sprint8_ctx():
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
async def client(sprint8_ctx):
    return sprint8_ctx["client"]


def _ctx_value(name: str):
    @pytest_asyncio.fixture(name=name)
    async def fixture(sprint8_ctx):
        return sprint8_ctx[name]
    return fixture


admin_token = _ctx_value("admin_token")
teacher_token = _ctx_value("teacher_token")
student_token = _ctx_value("student_token")
student_id = _ctx_value("student_id")
group_id = _ctx_value("group_id")
class_id = _ctx_value("class_id")
session_id = _ctx_value("session_id")


async def test_get_my_classes(client, teacher_token):
    r = await client.get(
        "/api/classes/my",
        headers={"Authorization": f"Bearer {teacher_token}"},
    )
    if r.status_code != 200:
        print("GET MY CLASSES ERROR:", r.text)
    assert r.status_code == 200
    d = r.json()["data"]
    assert "classes" in d
    assert "substituteGroups" in d
    assert len(d["classes"]) == 1


async def test_create_and_list_assignment(client, teacher_token, group_id, session_id):
    # 1. Create
    due = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
    r = await client.post(
        "/api/assignments",
        headers={"Authorization": f"Bearer {teacher_token}"},
        json={
            "groupId": group_id,
            "sessionId": session_id,
            "title": "Test Assignment",
            "description": "Desc",
            "dueDate": due,
            "files": []
        }
    )
    assert r.status_code == 201
    d = r.json()["data"]
    assert d["title"] == "Test Assignment"
    assignment_id = d["id"]

    # 2. List
    r2 = await client.get(
        "/api/assignments",
        headers={"Authorization": f"Bearer {teacher_token}"},
        params={"groupId": group_id}
    )
    assert r2.status_code == 200
    d2 = r2.json()["data"]
    assert len(d2["items"]) == 1
    assert d2["items"][0]["id"] == assignment_id
    assert d2["stats"]["total"] == 1


async def test_bulk_create_assignments(client, teacher_token, group_id):
    r = await client.post(
        "/api/assignments/bulk-create",
        headers={"Authorization": f"Bearer {teacher_token}"},
        json={
            "groupIds": [group_id],
            "title": "Bulk Assignment",
            "description": "Bulk Desc",
            "dueDate": None,
            "files": [{"fileUrl": "http://example.com/file.pdf"}]
        }
    )
    assert r.status_code == 201
    d = r.json()["data"]
    assert "batchId" in d
    assert d["createdCount"] == 1
    assert len(d["assignments"]) == 1


async def test_submit_assignment(client, teacher_token, student_token, group_id, student_id):
    # Create assignment as teacher
    r = await client.post(
        "/api/assignments",
        headers={"Authorization": f"Bearer {teacher_token}"},
        json={
            "groupId": group_id,
            "title": "Test Submit",
            "dueDate": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        }
    )
    assignment_id = r.json()["data"]["id"]

    # Submit as student
    r2 = await client.post(
        f"/api/assignments/{assignment_id}/submit",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "submissionType": "text",
            "responseText": "My homework"
        }
    )
    assert r2.status_code == 200
    sub = r2.json()["data"]
    assert sub["submissionType"] == "text"
    assert sub["responseText"] == "My homework"
    assert sub["studentId"] == student_id


async def test_get_submissions_roster(client, admin_token, teacher_token, student_token, group_id):
    r = await client.post(
        "/api/assignments",
        headers={"Authorization": f"Bearer {teacher_token}"},
        json={"groupId": group_id, "title": "Roster Test"}
    )
    assignment_id = r.json()["data"]["id"]

    await client.post(
        f"/api/assignments/{assignment_id}/submit",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"submissionType": "done_only"}
    )

    r2 = await client.get(
        f"/api/assignments/{assignment_id}/submissions",
        headers={"Authorization": f"Bearer {teacher_token}"}
    )
    assert r2.status_code == 200
    d = r2.json()["data"]
    assert d["summary"]["submittedCount"] == 1
    assert d["summary"]["notSubmittedCount"] == 0
    assert len(d["roster"]) == 1
    assert d["roster"][0]["submission"] is not None
