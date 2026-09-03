"""
Sprint 9 backend endpoint tests.
"""
from __future__ import annotations
from datetime import date, datetime, time, timedelta, timezone
import os
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.app import create_app
from src.core.database import Base, get_db
from src.core.security import create_access_token, hash_password
from src.modules.users.models import User
from src.modules.branches.models import Branch
from src.modules.modules.models import Module
from src.modules.classes.models import Class
from src.modules.groups.models import Group
from src.modules.sessions.models import Session
from src.modules.enrollments.models import Enrollment
from src.modules.attendance.models import Attendance
from src.modules.assignments.models import Assignment, AssignmentSubmission
from src.modules.config.models import SystemConfig


TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres1:password1@localhost:5432/psp_sprint8_test",
)

def _assert_local_test_database(url: str):
    parsed = make_url(url)
    if "test" not in (parsed.database or "").lower() and "localhost" not in (parsed.host or "").lower():
        raise RuntimeError("TEST_DATABASE_URL does not appear to be a local or test DB.")


async def _seed(db):
    branch = Branch(name="S9 Branch", is_active=True, address="Address", phone="123456789")
    db.add(branch)
    await db.flush()

    mod = Module(name="S9 Module", description="Desc")
    db.add(mod)
    await db.flush()

    admin = User(
        email="s9_admin@test.com", password_hash=hash_password("pw"), first_name="A", last_name="A",
        phone="000", status="active", role="admin"
    )
    t_user = User(
        email="s9_teacher@test.com", password_hash=hash_password("pw"), first_name="T", last_name="T",
        phone="111", status="active", role="teacher"
    )
    s_user = User(
        email="s9_student@test.com", password_hash=hash_password("pw"), first_name="S", last_name="S",
        phone="222", status="active", role="student"
    )
    s_user_not_enrolled = User(
        email="s9_student2@test.com", password_hash=hash_password("pw"), first_name="S2", last_name="S2",
        phone="333", status="active", role="student"
    )
    db.add_all([admin, t_user, s_user, s_user_not_enrolled])
    await db.flush()

    cls1 = Class(
        name="S9 Class Middle", module_id=mod.id, branch_id=branch.id, status="active",
        education_stage="middle", education_year=2, min_age=12, max_age=15, created_by=admin.id,
        teacher_id=t_user.id
    )
    cls2 = Class(
        name="S9 Class High", module_id=mod.id, branch_id=branch.id, status="active",
        education_stage="high", education_year=1, min_age=15, max_age=18, created_by=admin.id,
        teacher_id=t_user.id
    )
    db.add_all([cls1, cls2])
    await db.flush()

    grp1 = Group(class_id=cls1.id, name="S9 G1", max_students=20, price=100, subscription_type="monthly", teacher_id=t_user.id, room="Room 1")
    grp2 = Group(class_id=cls2.id, name="S9 G2", max_students=20, price=100, subscription_type="monthly", teacher_id=t_user.id, room="Room 2")
    db.add_all([grp1, grp2])
    await db.flush()

    now = datetime.now(timezone.utc)
    sess1 = Session(group_id=grp1.id, branch_id=branch.id, session_date=date.today(), start_time=time(10,0), end_time=time(12,0), room="Room 1", status="completed")
    sess2 = Session(group_id=grp2.id, branch_id=branch.id, session_date=date.today(), start_time=time(14,0), end_time=time(16,0), room="Room 2", status="scheduled")
    db.add_all([sess1, sess2])
    await db.flush()

    enr1 = Enrollment(student_id=s_user.id, group_id=grp1.id, branch_id=branch.id, status="active", source="self")
    enr_pending = Enrollment(student_id=s_user.id, group_id=grp2.id, branch_id=branch.id, status="pending", source="self")
    db.add_all([enr1, enr_pending])
    await db.flush()

    att = Attendance(session_id=sess1.id, student_id=s_user.id, status="present")
    db.add(att)
    await db.flush()

    assign = Assignment(group_id=grp1.id, class_id=cls1.id, title="S9 Assign", created_by=t_user.id, due_date=now + timedelta(days=1))
    db.add(assign)
    await db.flush()

    sub = AssignmentSubmission(assignment_id=assign.id, student_id=s_user.id, submission_type="text", response_text="Done", submitted_at=now, updated_at=now)
    db.add(sub)
    
    db.add(SystemConfig(enrollment_reservation_hold_hours=72))
    await db.flush()

    return {
        "cls1_id": cls1.id, "cls2_id": cls2.id, "grp1_id": grp1.id, "grp2_id": grp2.id,
        "sess1_id": sess1.id, "sess2_id": sess2.id, 
        "t_token": create_access_token({"sub": str(t_user.id)}), 
        "s_token": create_access_token({"sub": str(s_user.id)}),
        "s_not_enrolled_token": create_access_token({"sub": str(s_user_not_enrolled.id)}), 
        "assign_id": assign.id,
    }


@pytest_asyncio.fixture
async def sprint9_ctx():
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
async def client(sprint9_ctx):
    return sprint9_ctx["client"]


def _ctx_value(name: str):
    @pytest.fixture
    def f(sprint9_ctx):
        return sprint9_ctx[name]
    return f

cls1_id = _ctx_value("cls1_id")
cls2_id = _ctx_value("cls2_id")
grp1_id = _ctx_value("grp1_id")
grp2_id = _ctx_value("grp2_id")
sess1_id = _ctx_value("sess1_id")
sess2_id = _ctx_value("sess2_id")
t_token = _ctx_value("t_token")
s_token = _ctx_value("s_token")
s_not_enrolled_token = _ctx_value("s_not_enrolled_token")
assign_id = _ctx_value("assign_id")


@pytest.mark.asyncio
async def test_public_catalog_with_class_id_filter(client, cls1_id):
    response = await client.get(f"/api/public/catalog?classId={cls1_id}")
    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert len(items) > 0
    assert all(item["classId"] == cls1_id for item in items)


@pytest.mark.asyncio
async def test_public_catalog_with_education_stage_filter(client):
    response = await client.get("/api/public/catalog?educationStage=middle")
    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert len(items) > 0
    assert all(item["level"]["educationStage"] == "middle" for item in items)


@pytest.mark.asyncio
async def test_public_catalog_includes_level_field(client):
    response = await client.get("/api/public/catalog")
    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert len(items) > 0
    assert all("level" in item for item in items)
    assert any(item["level"] is not None and item["level"]["educationStage"] == "high" for item in items)


@pytest.mark.asyncio
async def test_sessions_list_with_group_ids_filter(client, t_token, grp1_id):
    from datetime import date, timedelta
    date_from = date.today().isoformat()
    date_to = (date.today() + timedelta(days=7)).isoformat()
    response = await client.get(
        f"/api/sessions?groupIds={grp1_id}&dateFrom={date_from}&dateTo={date_to}",
        headers={"Authorization": f"Bearer {t_token}"}
    )
    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert len(items) > 0
    assert all(item["groupId"] == grp1_id for item in items)


@pytest.mark.asyncio
async def test_session_detail_my_attendance_for_enrolled_student(client, s_token, sess1_id):
    response = await client.get(f"/api/sessions/{sess1_id}", headers={"Authorization": f"Bearer {s_token}"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["myAttendance"] is not None
    assert data["myAttendance"]["status"] == "present"


@pytest.mark.asyncio
async def test_assignments_list_widened_auth_for_student(client, s_token):
    response = await client.get("/api/assignments", headers={"Authorization": f"Bearer {s_token}"})
    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert len(items) > 0


@pytest.mark.asyncio
async def test_assignments_list_403_not_enrolled(client, s_not_enrolled_token):
    response = await client.get("/api/assignments", headers={"Authorization": f"Bearer {s_not_enrolled_token}"})
    assert response.status_code == 403
    assert "ASSIGNMENT_NOT_ENROLLED" in str(response.json())


@pytest.mark.asyncio
async def test_assignments_student_sees_my_submission(client, s_token, assign_id):
    response = await client.get("/api/assignments", headers={"Authorization": f"Bearer {s_token}"})
    assert response.status_code == 200
    items = response.json()["data"]["items"]
    test_item = next((i for i in items if i["id"] == assign_id), None)
    assert test_item is not None
    assert test_item["mySubmission"] is not None
    assert test_item["mySubmission"]["responseText"] == "Done"


@pytest.mark.asyncio
async def test_enrollment_countdown_on_all_pending(client, s_token):
    response = await client.get("/api/enrollments/my", headers={"Authorization": f"Bearer {s_token}"})
    assert response.status_code == 200
    items = response.json()["data"]["items"]
    pending = next((i for i in items if i["status"] == "pending"), None)
    assert pending is not None
    assert pending["reservationExpiresAt"] is not None
    assert "isOverdue" in pending
