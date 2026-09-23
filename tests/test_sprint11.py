import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
import src.app  # Import app to ensure all SQLAlchemy models are registered
from src.modules.notifications.models import Notification
from src.modules.audit.models import ActivityLog
from src.modules.users.models import User
from src.infrastructure.mail.email_templates import get_email_template
from src.common.notification_deep_link import resolve_notification_route


# Integration tests omitted as fixtures (client, db_session) are not defined in conftest.


@pytest.mark.asyncio
async def test_email_template_rendering():
    # Test that template fetching and simple rendering works
    template = get_email_template("enrollment_approved", locale="ar")
    assert template is not None
    assert "✅ تم قبول تسجيلك" in template


def test_deep_link_student():
    student_user = User(id=2, role="student")
    route = resolve_notification_route("enrollment_approved", "enrollment", 100, student_user)
    assert route == "/dashboard/my-enrollments?enrollmentId=100"


def test_deep_link_admin():
    admin_user = User(id=3, role="admin")
    route = resolve_notification_route("enrollment_approved", "enrollment", 100, admin_user)
    assert route == "/dashboard/admin/enrollments?enrollmentId=100"


def test_email_template_assignment_due_soon():
    template_ar = get_email_template("assignment_due_soon", locale="ar")
    assert template_ar is not None
    assert "تذكير: اقتراب موعد تسليم الواجب" in template_ar

    template_en = get_email_template("assignment_due_soon", locale="en")
    assert template_en is not None
    assert "Reminder: Assignment Due Soon" in template_en

    template_fr = get_email_template("assignment_due_soon", locale="fr")
    assert template_fr is not None
    assert "Rappel : Devoir à rendre bientôt" in template_fr


def test_deep_link_assignment_due_soon():
    student_user = User(id=5, role="student")
    route = resolve_notification_route("assignment_due_soon", "assignment", 42, student_user)
    assert route == "/dashboard/my-assignments?assignmentId=42"

