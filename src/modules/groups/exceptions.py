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
