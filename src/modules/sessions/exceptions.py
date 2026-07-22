from src.core.exceptions import AppException


class SessionNotFound(AppException):
    status_code = 404
    code = "NOT_FOUND"
    message = "Session not found."


class AttendanceAlreadyMarked(AppException):
    status_code = 409
    code = "ATTENDANCE_ALREADY_MARKED"
    message = "Attendance has already been marked for this session."
