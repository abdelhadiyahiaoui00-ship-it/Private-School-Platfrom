from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import PermissionDenied


class NotTeamLeader(PermissionDenied):
    message = "You must be the team leader to perform this action."


def owns_resource(user_id: int, resource_owner_id: int) -> bool:
    return user_id == resource_owner_id


def require_ownership(user_id: int, resource_owner_id: int) -> None:
    if not owns_resource(user_id, resource_owner_id):
        raise PermissionDenied(message="You do not own this resource.")


async def is_team_member(user_id: int, team_id: int, session: AsyncSession) -> bool:
    from src.modules.teams.models import TeamMember
    from src.modules.students.models import Student

    result = await session.execute(
        select(TeamMember.id)
        .join(Student, Student.id == TeamMember.student_id)
        .where(Student.user_id == user_id, TeamMember.team_id == team_id)
    )
    return result.scalar_one_or_none() is not None


async def is_team_leader(user_id: int, team_id: int, session: AsyncSession) -> bool:
    from src.modules.teams.models import Team
    from src.modules.students.models import Student

    result = await session.execute(
        select(Team.id)
        .join(Student, Student.id == Team.leader_id)
        .where(Student.user_id == user_id, Team.id == team_id)
    )
    return result.scalar_one_or_none() is not None


async def require_team_leader(user_id: int, team_id: int, session: AsyncSession) -> None:
    if not await is_team_leader(user_id, team_id, session):
        raise NotTeamLeader()
