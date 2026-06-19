from src.common.enums import ProjectStatus
from src.core.exceptions import InvalidStateTransition


class ProjectStateMachine:
    VALID_TRANSITIONS: dict[ProjectStatus, list[ProjectStatus]] = {
        ProjectStatus.DRAFT: [ProjectStatus.PENDING],
        ProjectStatus.PENDING: [ProjectStatus.ACCEPTED, ProjectStatus.REJECTED],
        ProjectStatus.ACCEPTED: [ProjectStatus.ASSIGNED],
        ProjectStatus.REJECTED: [ProjectStatus.PENDING],
        ProjectStatus.ASSIGNED: [ProjectStatus.IN_PROGRESS],
        ProjectStatus.IN_PROGRESS: [ProjectStatus.AUTHORIZATION_SUBMITTED, ProjectStatus.CANCELLED],
        ProjectStatus.AUTHORIZATION_SUBMITTED: [ProjectStatus.DEFENSE_SCHEDULED, ProjectStatus.IN_PROGRESS],
        ProjectStatus.DEFENSE_SCHEDULED: [ProjectStatus.DEFENDED],
        ProjectStatus.DEFENDED: [ProjectStatus.COMPLETED],
        ProjectStatus.COMPLETED: [],
        ProjectStatus.CANCELLED: [],
    }

    def transition(self, current: ProjectStatus, target: ProjectStatus) -> ProjectStatus:
        allowed = self.VALID_TRANSITIONS.get(current, [])
        if target not in allowed:
            raise InvalidStateTransition(
                message=f"Cannot transition from {current.value} to {target.value}. "
                        f"Allowed: {[s.value for s in allowed]}"
            )
        return target

    def get_allowed_transitions(self, current: ProjectStatus) -> list[ProjectStatus]:
        return self.VALID_TRANSITIONS.get(current, [])
