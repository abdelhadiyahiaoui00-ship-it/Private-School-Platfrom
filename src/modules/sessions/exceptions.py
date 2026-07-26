from src.core.exceptions import AppException


class SessionNotFound(AppException):
    status_code = 404
    code = "NOT_FOUND"
    message = "Session not found."


class DateRangeTooWide(AppException):
    status_code = 422
    code = "DATE_RANGE_TOO_WIDE"
    message = "Date range cannot exceed 62 days."


class InvalidStatusTransition(AppException):
    status_code = 422
    code = "INVALID_STATUS_TRANSITION"
    message = "Invalid status transition for this session."


class SessionHasAttendance(AppException):
    status_code = 409
    code = "SESSION_HAS_ATTENDANCE"
    message = "Cannot delete a session that has attendance records."


class AttendanceAlreadyMarked(AppException):
    status_code = 409
    code = "ATTENDANCE_ALREADY_MARKED"
    message = "Attendance has already been marked for this session."
