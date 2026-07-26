from src.core.exceptions import AppException


class GroupNotFound(AppException):
    status_code = 404
    code = "NOT_FOUND"
    message = "Group not found."


class GroupHasActiveDependencies(AppException):
    status_code = 409
    code = "GROUP_HAS_ACTIVE_DEPENDENCIES"
    message = "Cannot delete a group that has enrollments or sessions."


class InvalidScheduleFormat(AppException):
    status_code = 422
    code = "INVALID_SCHEDULE_FORMAT"
    message = "Schedule format is invalid."


class CannotChangeSubscriptionType(AppException):
    status_code = 422
    code = "CANNOT_CHANGE_SUBSCRIPTION_TYPE"
    message = "Cannot change subscription type if there are active enrollments."


class ScheduleOverlap(AppException):
    status_code = 422
    code = "SCHEDULE_OVERLAP"
    message = "Schedule overlaps with an existing group."


class ScheduleRequired(AppException):
    status_code = 422
    code = "SCHEDULE_REQUIRED"
    message = "Schedule is required for this group type."


class SessionCountRequired(AppException):
    status_code = 422
    code = "SESSION_COUNT_REQUIRED"
    message = "Session count is required for session-based groups."
