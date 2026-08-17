from src.core.exceptions import AppException


class AttendanceSessionNotMarkable(AppException):
    status_code = 422
    code = "ATTENDANCE_SESSION_NOT_MARKABLE"
    message = "Session is not in a markable state, or is dated in the future."


class CannotMarkPresentSubscriptionExpired(AppException):
    status_code = 422
    code = "CANNOT_MARK_PRESENT_SUBSCRIPTION_EXPIRED"
    message = "One or more students cannot be marked present - subscription expired or missing."


class SessionNotReschedulable(AppException):
    status_code = 409
    code = "SESSION_NOT_RESCHEDULABLE"
    message = "Session is not in 'scheduled' status, or its date has already passed."


class RescheduleTargetInvalid(AppException):
    status_code = 422
    code = "RESCHEDULE_TARGET_INVALID"
    message = "Proposed end time must be after start time, and date must be valid."


class RescheduleRequestAlreadyPending(AppException):
    status_code = 409
    code = "RESCHEDULE_REQUEST_ALREADY_PENDING"
    message = "A pending reschedule request already exists for this session."


class RescheduleRequestAlreadyResolved(AppException):
    status_code = 409
    code = "RESCHEDULE_REQUEST_ALREADY_RESOLVED"
    message = "This reschedule request has already been approved or rejected."


class SessionStatusInvalidForAction(AppException):
    status_code = 409
    code = "SESSION_STATUS_INVALID_FOR_ACTION"
    message = "Session status does not allow this action."
