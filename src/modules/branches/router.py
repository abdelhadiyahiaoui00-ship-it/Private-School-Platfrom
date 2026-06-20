from fastapi import APIRouter
from src.core.database import DBSessionDep
from src.modules.auth.dependencies import CurrentUser
from src.modules.branches.models import Branch
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from src.modules.users.models import UserBranch

router = APIRouter(prefix="/branches", tags=["Branches"])


@router.get("/my", summary="Get branches accessible to current user")
async def get_my_branches(
    actor: CurrentUser,
    session: DBSessionDep,
):
    """
    - owner / superAdmin: returns ALL active branches
    - admin / teacher: returns only assigned branches
    - student / parent: returns empty list (they don't use branch switcher)
    """
    if actor.role in ("owner", "superAdmin"):
        result = await session.execute(
            select(Branch).where(Branch.is_active == True).order_by(Branch.name)
        )
        branches = result.scalars().all()
    elif actor.role in ("admin", "teacher"):
        result = await session.execute(
            select(Branch)
            .join(UserBranch, UserBranch.branch_id == Branch.id)
            .where(UserBranch.user_id == actor.id, Branch.is_active == True)
            .order_by(Branch.name)
        )
        branches = result.scalars().all()
    else:
        branches = []

    return {
        "data": [
            {"id": b.id, "name": b.name, "isActive": b.is_active}
            for b in branches
        ]
    }
