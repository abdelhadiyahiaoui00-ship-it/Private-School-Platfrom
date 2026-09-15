"""
notification_deep_link.py — Sprint 11

Role-aware deep-link resolver for notification routing.
Populates the Notification.link field at creation time so that
the frontend can navigate directly to the relevant entity.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.modules.users.models import User


def resolve_notification_route(
    notification_type: str,
    entity_type: str | None,
    entity_id: int | None,
    user: "User | None",
) -> str | None:
    """
    Return a dashboard deep-link URL for a notification.

    Rules:
    - student / parent  → /dashboard/my-*
    - teacher           → /dashboard/sessions (or session detail)
    - admin / superAdmin / owner → /dashboard/admin/*

    Returns None if user is None or role is unrecognised.
    """
    if not user:
        return None

    role = getattr(user, "role", None)

    # ── Student / Parent ──────────────────────────────────────────────────────
    if role in ("student", "parent"):
        if notification_type == "enrollment_approved" and entity_type == "enrollment" and entity_id:
            return f"/dashboard/my-enrollments?enrollmentId={entity_id}"
        if notification_type == "enrollment_rejected" and entity_type == "enrollment" and entity_id:
            return f"/dashboard/my-enrollments?enrollmentId={entity_id}"
        if notification_type == "enrollment_group_transferred" and entity_type == "enrollment" and entity_id:
            return f"/dashboard/my-enrollments?enrollmentId={entity_id}"
        if notification_type in ("subscription_expiring", "subscription_expired"):
            if entity_type == "subscription" and entity_id:
                return f"/dashboard/my-subscriptions?subscriptionId={entity_id}"
            return "/dashboard/my-subscriptions"
        if notification_type == "payment_confirmed":
            return "/dashboard/my-subscriptions"
        if notification_type == "assignment_submitted" and entity_type == "session" and entity_id:
            return f"/dashboard/sessions/{entity_id}"
        # Fallback
        return "/dashboard/my-enrollments"

    # ── Teacher ───────────────────────────────────────────────────────────────
    if role == "teacher":
        if notification_type == "assignment_submitted" and entity_type == "session" and entity_id:
            return f"/dashboard/sessions/{entity_id}"
        if notification_type == "session_rescheduled" and entity_type == "session" and entity_id:
            return f"/dashboard/sessions/{entity_id}"
        if entity_type == "session" and entity_id:
            return f"/dashboard/sessions/{entity_id}"
        return "/dashboard/sessions"

    # ── Admin / SuperAdmin / Owner ────────────────────────────────────────────
    if role in ("admin", "superAdmin", "owner"):
        if notification_type in ("enrollment_approved", "enrollment_rejected") and entity_type == "enrollment" and entity_id:
            return f"/dashboard/admin/enrollments?enrollmentId={entity_id}"
        if notification_type == "enrollment_group_transferred" and entity_type == "enrollment" and entity_id:
            return f"/dashboard/admin/enrollments?enrollmentId={entity_id}"
        if notification_type == "payment_confirmed" and entity_type == "payment" and entity_id:
            return f"/dashboard/admin/subscriptions?paymentId={entity_id}"
        if notification_type == "assignment_submitted" and entity_type == "session" and entity_id:
            return f"/dashboard/admin/sessions/{entity_id}"
        if entity_type == "enrollment" and entity_id:
            return f"/dashboard/admin/enrollments?enrollmentId={entity_id}"
        return "/dashboard/admin/enrollments"

    return None
