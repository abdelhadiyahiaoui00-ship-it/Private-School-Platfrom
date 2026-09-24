import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import src.app  # Register models
from src.modules.assignments.service import AssignmentService
from src.modules.users.models import User, ParentStudentLink
from src.modules.assignments.models import Assignment, AssignmentSubmission
from src.core.exceptions import PermissionDenied


@pytest.mark.asyncio
async def test_parent_viewer_student_id_valid_access():
    mock_session = AsyncMock()

    parent_user = User(id=10, role="parent")

    link = ParentStudentLink(parent_id=10, student_id=5)
    mock_link_res = MagicMock()
    mock_link_res.scalar_one_or_none.return_value = link

    assignment = MagicMock(spec=Assignment)
    assignment.id = 100
    assignment.group_id = 1
    assignment.class_id = 2
    assignment.due_date = None

    submission = MagicMock(spec=AssignmentSubmission)
    submission.id = 500
    submission.assignment_id = 100
    submission.student_id = 5
    submission.submission_type = "text"
    submission.response_text = "Child submission"
    submission.file_url = None
    submission.file_name = None
    submission.file_type = None
    submission.submitted_at = datetime.now(timezone.utc)
    submission.updated_at = datetime.now(timezone.utc)

    mock_count = MagicMock()
    mock_count.scalar.return_value = 1

    mock_assignments_res = MagicMock()
    mock_assignments_res.scalars.return_value.all.return_value = [assignment]

    mock_sub_res = MagicMock()
    mock_sub_res.scalar_one_or_none = MagicMock(return_value=submission)

    service = AssignmentService(mock_session)
    service._due_soon_hours = AsyncMock(return_value=24)
    service._get_student_active_group_ids = AsyncMock(return_value=[1])
    service._build = AsyncMock(return_value={"id": 100, "title": "Test Assignment"})
    service._compute_stats = AsyncMock(return_value={"total": 1, "upcoming": 0, "dueSoon": 0, "overdue": 0})

    mock_session.execute.side_effect = [
        mock_link_res,          # parent-child link check
        mock_count,             # count query
        mock_assignments_res,   # assignments query
        mock_sub_res,           # submission query for student 5
    ]

    filters = {"viewerStudentId": 5, "groupId": 1}
    res = await service.list_assignments(
        actor_id=10,
        is_admin=False,
        filters=filters,
        page=1,
        page_size=20,
        actor=parent_user,
    )

    assert "items" in res
    assert len(res["items"]) == 1
    item = res["items"][0]
    assert item["mySubmission"] is not None
    assert item["mySubmission"]["studentId"] == 5


@pytest.mark.asyncio
async def test_parent_viewer_student_id_unlinked_child_raises_403():
    mock_session = AsyncMock()
    parent_user = User(id=10, role="parent")

    # Link does not exist
    mock_link_res = MagicMock()
    mock_link_res.scalar_one_or_none.return_value = None

    mock_session.execute.return_value = mock_link_res

    service = AssignmentService(mock_session)

    filters = {"viewerStudentId": 999, "groupId": 1}
    with pytest.raises(PermissionDenied):
        await service.list_assignments(
            actor_id=10,
            is_admin=False,
            filters=filters,
            page=1,
            page_size=20,
            actor=parent_user,
        )


@pytest.mark.asyncio
async def test_student_ignores_viewer_student_id():
    mock_session = AsyncMock()
    student_user = User(id=5, role="student")

    assignment = MagicMock(spec=Assignment)
    assignment.id = 100
    assignment.group_id = 1
    assignment.due_date = None

    mock_count = MagicMock()
    mock_count.scalar.return_value = 1

    mock_assignments_res = MagicMock()
    mock_assignments_res.scalars.return_value.all.return_value = [assignment]

    mock_sub_res = MagicMock()
    mock_sub_res.scalar_one_or_none.return_value = None

    service = AssignmentService(mock_session)
    service._due_soon_hours = AsyncMock(return_value=24)
    service._get_student_active_group_ids = AsyncMock(return_value=[1])
    service._build = AsyncMock(return_value={"id": 100, "title": "Test Assignment"})
    service._compute_stats = AsyncMock(return_value={"total": 1, "upcoming": 0, "dueSoon": 0, "overdue": 0})

    mock_session.execute.side_effect = [
        mock_count,
        mock_assignments_res,
        mock_sub_res,
    ]

    # Student passes viewerStudentId=999
    filters = {"viewerStudentId": 999, "groupId": 1}
    res = await service.list_assignments(
        actor_id=5,
        is_admin=False,
        filters=filters,
        page=1,
        page_size=20,
        actor=student_user,
    )

    # Should NOT throw 403, ignores viewerStudentId and uses student's own ID (5)
    assert "items" in res
