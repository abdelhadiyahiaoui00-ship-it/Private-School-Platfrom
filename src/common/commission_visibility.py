"""
Commission Visibility — Sprint 10.

Determines whether a requesting user may see commission-sensitive fields
(commissionPercent, commissionAmount, netAmount, effectiveCommissionPercent,
defaultCommissionPercent).

Rules:
- owner / superAdmin: always visible
- teacher: visible only for their OWN classes/groups (context_teacher_id == user.id)
- admin, student, parent, unauthenticated: never visible

This is the single authoritative function. Apply it in every service response
builder. Never replicate the logic inline.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.modules.users.models import User


def resolve_commission_visibility(
    user: "User | None",
    context_teacher_id: int | None = None,
) -> bool:
    """
    Returns True if the viewer may see commission fields.

    Parameters
    ----------
    user:
        The authenticated actor (None = unauthenticated).
    context_teacher_id:
        The teacher_id of the class/group/subscription being viewed.
        Required when the user is a teacher so we can check ownership.
    """
    if not user:
        return False

    if user.role in ("owner", "superAdmin"):
        return True

    if user.role == "teacher":
        return context_teacher_id is not None and context_teacher_id == user.id

    return False
