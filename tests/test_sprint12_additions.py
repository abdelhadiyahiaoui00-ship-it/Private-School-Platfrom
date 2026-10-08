import pytest
from datetime import date, datetime, time, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException

import src.app  # Register SQLAlchemy models
from src.modules.assignments.service import AssignmentService
from src.modules.attendance.service import AttendanceService
from src.modules.branches.models import Branch
from src.modules.classes.models import Class
from src.core.exceptions import PermissionDenied
from src.modules.groups.models import Group
from src.modules.modules.models import Module
from src.modules.sessions.models import Session
from src.modules.sessions.service import SessionService
from src.modules.subscriptions.service import SubscriptionService
from src.modules.subscriptions.models import Subscription
from src.modules.config.service import ConfigService
from src.modules.config.models import SystemConfig
from src.modules.users.models import User, ParentStudentLink



@pytest.mark.asyncio
async def test_get_my_classes_substitute_groups():
    """Verify GET /classes/my substituteGroups returns active groups where actor is substitute."""
    mock_session = AsyncMock()

    teacher_owner = User(id=1, first_name="Owner", last_name="Teacher", role="teacher")
    teacher_sub = User(id=2, first_name="Sub", last_name="Teacher", role="teacher")

    cls = Class(
        id=10,
        name="Math 101",
        teacher_id=1,
        status="active",
        module_id=1,
        branch_id=1,
    )
    cls.teacher = teacher_owner
    cls.module = MagicMock(name="Math")
    cls.branch = MagicMock(name="Main Branch")

    # Group 1 is taught by substitute Teacher 2 under Class 10 (owned by Teacher 1)
    group_sub = Group(
        id=100,
        name="Group Sub",
        class_id=10,
        teacher_id=2,
        max_students=20,
        status="active",
    )

    # Mock DB queries for Teacher 2 (substitute teacher)
    mock_owned_res = MagicMock()
    mock_owned_res.scalars.return_value.all.return_value = []  # Teacher 2 owns 0 classes

    mock_sub_res = MagicMock()
    mock_sub_res.scalars.return_value.all.return_value = [group_sub]

    mock_cls_res = MagicMock()
    mock_cls_res.scalar_one_or_none.return_value = cls

    mock_session.execute.side_effect = [
        mock_owned_res,  # query owned classes
        mock_sub_res,    # query substitute groups
        mock_cls_res,    # query parent class details for substitute group
    ]

    service = AssignmentService(mock_session)
    res = await service.get_my_classes(teacher_id=2)

    assert res["classes"] == []
    assert len(res["substituteGroups"]) == 1
    sub_g = res["substituteGroups"][0]
    assert sub_g["id"] == 100
    assert sub_g["name"] == "Group Sub"
    assert sub_g["parentClass"]["id"] == 10
    assert sub_g["parentClass"]["defaultTeacherName"] == "Owner Teacher"


@pytest.mark.asyncio
async def test_get_my_subscriptions_student_access():
    """Verify GET /subscriptions/my for student role and accurate isExpired/status logic."""
    mock_session = AsyncMock()

    student_user = User(id=5, role="student", first_name="Ali", last_name="Ben")

    group = MagicMock(spec=Group)
    group.name = "Physics A"
    group.class_ = MagicMock()
    group.class_.id = 1
    group.class_.name = "Physics"
    group.class_.module = MagicMock()
    group.class_.module.name = "Science"
    group.teacher = None

    # Sub 1: Monthly expired 5 days ago
    sub1 = Subscription(
        id=1,
        enrollment_id=10,
        student_id=5,
        group_id=1,
        branch_id=1,
        teacher_id=2,
        module_id=1,
        type="monthly",
        status="active",
        price=1000.0,
        start_date=date.today() - timedelta(days=35),
        end_date=date.today() - timedelta(days=5),
        total_sessions=None,
        remaining_sessions=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    sub1.student = student_user
    sub1.group = group
    sub1.teacher = None
    branch_mock = MagicMock()
    branch_mock.name = "Main"
    sub1.branch = branch_mock

    # Sub 2: Active monthly
    sub2 = Subscription(
        id=2,
        enrollment_id=11,
        student_id=5,
        group_id=1,
        branch_id=1,
        teacher_id=2,
        module_id=1,
        type="monthly",
        status="active",
        price=1000.0,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=25),
        total_sessions=None,
        remaining_sessions=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    sub2.student = student_user
    sub2.group = group
    sub2.teacher = None
    sub2.branch = branch_mock

    mock_subs_res = MagicMock()
    mock_subs_res.scalars.return_value.all.return_value = [sub1, sub2]

    mock_session.execute.return_value = mock_subs_res

    service = SubscriptionService(mock_session)
    service.sub_repo.get_latest_subscription_ids = AsyncMock(return_value={10: 1, 11: 2})

    items = await service.get_my_subscriptions(actor=student_user, student_ids=[5])

    assert len(items) == 2

    # Expired sub check
    item1 = next(i for i in items if i["id"] == 1)
    assert item1["isExpired"] is True
    assert item1["status"] == "expired"
    assert item1["groupId"] == 1

    # Active sub check
    item2 = next(i for i in items if i["id"] == 2)
    assert item2["isExpired"] is False
    assert item2["status"] == "active"
    assert item2["groupId"] == 1

    # Forbidden check: student querying another student
    with pytest.raises(HTTPException) as exc_info:
        await service.get_my_subscriptions(actor=student_user, student_ids=[6])
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_get_my_subscriptions_parent_access():
    """Verify GET /subscriptions/my for parent role with child verification."""
    mock_session = AsyncMock()

    parent_user = User(id=10, role="parent")
    student_user = User(id=5, role="student", first_name="Child", last_name="One")

    mock_links_res = MagicMock()
    mock_links_res.scalars.return_value.all.return_value = [5]  # Parent 10 is linked to Student 5

    group = MagicMock(spec=Group)
    group.name = "Math A"
    group.class_ = None
    group.teacher = None

    sub = Subscription(
        id=1,
        enrollment_id=10,
        student_id=5,
        group_id=2,
        branch_id=1,
        teacher_id=2,
        module_id=1,
        type="session_based",
        status="active",
        price=500.0,
        total_sessions=4,
        remaining_sessions=0,  # 0 remaining -> isExpired should be True
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    sub.student = student_user
    sub.group = group
    sub.teacher = None
    sub.branch = None

    mock_subs_res = MagicMock()
    mock_subs_res.scalars.return_value.all.return_value = [sub]

    mock_session.execute.side_effect = [
        mock_links_res,
        mock_subs_res,
    ]

    service = SubscriptionService(mock_session)
    service.sub_repo.get_latest_subscription_ids = AsyncMock(return_value={10: 1})

    items = await service.get_my_subscriptions(actor=parent_user, student_ids=[5])
    assert len(items) == 1
    assert items[0]["isExpired"] is True
    assert items[0]["status"] == "expired"

    # Parent querying unlinked student
    mock_links_res2 = MagicMock()
    mock_links_res2.scalars.return_value.all.return_value = [5]
    mock_session.execute.side_effect = [mock_links_res2]
    with pytest.raises(HTTPException) as exc_info:
        await service.get_my_subscriptions(actor=parent_user, student_ids=[99])
    assert exc_info.value.status_code == 403


def _session_detail_fixture() -> Session:
    now = datetime.now(timezone.utc)
    module = Module(id=3, name="Science")
    cls = Class(
        id=2,
        name="Physics",
        module_id=module.id,
        branch_id=1,
        teacher_id=20,
        education_stage="all",
        status="active",
    )
    cls.module = module
    cls.teacher = None

    group = Group(
        id=7,
        class_id=cls.id,
        name="Physics A",
        teacher_id=None,
        room="Room 1",
        max_students=20,
        price=1000,
        subscription_type="monthly",
        status="active",
    )
    group.class_ = cls
    group.teacher = None

    branch = Branch(id=1, name="Main Branch", is_active=True)

    sess = Session(
        id=11,
        group_id=group.id,
        branch_id=branch.id,
        session_date=date.today(),
        start_time=time(10, 0),
        end_time=time(12, 0),
        room="Room 1",
        status="completed",
        created_at=now,
        updated_at=now,
    )
    sess.group_ = group
    sess.branch = branch
    return sess


@pytest.mark.asyncio
async def test_get_session_allows_parent_with_enrolled_child():
    mock_session = AsyncMock()
    sess = _session_detail_fixture()

    parent_access_res = MagicMock()
    parent_access_res.scalar_one_or_none.return_value = 5
    mock_session.execute.return_value = parent_access_res

    service = SessionService(mock_session)
    service._repo = MagicMock()
    service._repo.get_by_id = AsyncMock(return_value=sess)
    service._get_my_attendance = AsyncMock(return_value={"status": "present"})

    parent_user = User(id=10, role="parent")
    data = await service.get_session(sess.id, parent_user)

    assert data["id"] == sess.id
    assert data["groupId"] == sess.group_id
    assert data["myAttendance"]["status"] == "present"
    service._get_my_attendance.assert_awaited_once_with(sess, 5)


@pytest.mark.asyncio
async def test_get_session_denies_parent_without_enrolled_child():
    mock_session = AsyncMock()
    sess = _session_detail_fixture()

    parent_access_res = MagicMock()
    parent_access_res.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = parent_access_res

    service = SessionService(mock_session)
    service._repo = MagicMock()
    service._repo.get_by_id = AsyncMock(return_value=sess)
    service._get_my_attendance = AsyncMock()

    parent_user = User(id=10, role="parent")
    with pytest.raises(PermissionDenied):
        await service.get_session(sess.id, parent_user)

    service._get_my_attendance.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_my_attendance_rejects_student_requesting_other_student():
    service = AttendanceService(AsyncMock())
    student_user = User(id=5, role="student")

    with pytest.raises(PermissionDenied):
        await service.get_my_attendance_matrix(
            group_id=7,
            actor=student_user,
            student_id=6,
        )


@pytest.mark.asyncio
async def test_get_my_attendance_parent_filters_to_linked_child():
    mock_session = AsyncMock()
    link_res = MagicMock()
    link_res.scalar_one_or_none.return_value = 1
    mock_session.execute.return_value = link_res

    service = AttendanceService(mock_session)
    service._student_has_group_history = AsyncMock(return_value=True)
    service._build_attendance_matrix = AsyncMock(
        return_value={"students": [{"student": {"id": 5}}]}
    )

    parent_user = User(id=10, role="parent")
    data = await service.get_my_attendance_matrix(
        group_id=7,
        actor=parent_user,
        student_id=5,
        direction="next",
        page_size=4,
    )

    assert data["students"][0]["student"]["id"] == 5
    service._build_attendance_matrix.assert_awaited_once()
    kwargs = service._build_attendance_matrix.await_args.kwargs
    assert kwargs["direction"] == "next"
    assert kwargs["page_size"] == 4
    assert kwargs["require_group_access"] is False
    assert kwargs["student_ids_filter"] == {5}
    assert kwargs["force_student_ids"] == {5}
    assert kwargs["include_sessions_when_empty"] is True


@pytest.mark.asyncio
async def test_get_my_attendance_denies_unlinked_parent_child():
    mock_session = AsyncMock()
    link_res = MagicMock()
    link_res.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = link_res

    service = AttendanceService(mock_session)
    service._student_has_group_history = AsyncMock()
    service._build_attendance_matrix = AsyncMock()

    parent_user = User(id=10, role="parent")
    with pytest.raises(PermissionDenied):
        await service.get_my_attendance_matrix(
            group_id=7,
            actor=parent_user,
            student_id=5,
        )

    service._student_has_group_history.assert_not_awaited()
    service._build_attendance_matrix.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_my_attendance_without_row_returns_empty_students():
    service = AttendanceService(AsyncMock())
    service._student_has_group_history = AsyncMock(return_value=False)
    service._build_attendance_matrix = AsyncMock(return_value={"students": []})

    student_user = User(id=5, role="student")
    data = await service.get_my_attendance_matrix(group_id=7, actor=student_user)

    assert data["students"] == []
    kwargs = service._build_attendance_matrix.await_args.kwargs
    assert kwargs["student_ids_filter"] == {5}
    assert kwargs["force_student_ids"] == set()


@pytest.mark.asyncio
async def test_get_my_attendance_denies_teacher_and_admin_roles():
    service = AttendanceService(AsyncMock())

    with pytest.raises(PermissionDenied):
        await service.get_my_attendance_matrix(
            group_id=7, actor=User(id=20, role="teacher")
        )

    with pytest.raises(PermissionDenied):
        await service.get_my_attendance_matrix(
            group_id=7, actor=User(id=30, role="admin")
        )


@pytest.mark.asyncio
async def test_system_config_about_video_art_image_urls():
    """Verify SystemConfig about_video_url and art_under_image_url updates."""
    mock_session = AsyncMock()

    config = SystemConfig(
        id=1,
        default_language="ar",
        school_name="Académie Al-Nour",
        about_title="About Us",
        about_description="Description",
        about_stats=[],
        about_video_url=None,
        art_under_image_url=None,
        social_links={},
        monthly_default_duration_days=30,
        monthly_expiry_warning_days=3,
        session_based_expiry_warning_sessions=3,
        session_generation_horizon_weeks=8,
        enrollment_reservation_hold_hours=72,
    )

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = config
    mock_session.execute.return_value = mock_res
    mock_session.merge.return_value = config

    service = ConfigService(mock_session)

    # Initial response check
    resp = await service.get()
    assert resp.about_video_url is None
    assert resp.art_under_image_url is None

    owner_user = User(id=1, role="owner")

    # Update with Cloudinary URLs
    update_data = {
        "about_video_url": "https://res.cloudinary.com/school/video/upload/about.mp4",
        "art_under_image_url": "https://res.cloudinary.com/school/image/upload/art.jpg",
    }

    mock_session.execute.return_value = mock_res
    updated_resp = await service.update(update_data, actor=owner_user)

    assert config.about_video_url == "https://res.cloudinary.com/school/video/upload/about.mp4"
    assert config.art_under_image_url == "https://res.cloudinary.com/school/image/upload/art.jpg"
    assert updated_resp.about_video_url == "https://res.cloudinary.com/school/video/upload/about.mp4"
    assert updated_resp.art_under_image_url == "https://res.cloudinary.com/school/image/upload/art.jpg"

    # Reset about_video_url to None
    reset_data = {"about_video_url": None}
    mock_session.execute.return_value = mock_res
    reset_resp = await service.update(reset_data, actor=owner_user)

    assert config.about_video_url is None
    assert reset_resp.about_video_url is None
